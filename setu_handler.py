"""Setu AA handler for PDR.
Auth: OAuth Bearer token (clientID + secret → accessToken)
Consent payload: ConsentDetail format per Setu AA v2 spec
"""

import requests
import time
import datetime
import uuid

SETU_BASE_URL   = "https://fiu-sandbox.setu.co"
SETU_TOKEN_URL  = "https://auth.setu.co/oauth2/token"
POLL_RETRIES    = 6
POLL_INTERVAL_S = 5


class SetuAAHandler:
    def __init__(self, client_id: str, client_secret: str, product_id: str):
        self.client_id     = client_id
        self.client_secret = client_secret
        self.product_id    = product_id
        self.base_url      = SETU_BASE_URL
        self._token        = None
        self._token_expiry = 0

    # ─────────────────────────────────────────
    # AUTH — OAuth Bearer token
    # ─────────────────────────────────────────

    def _get_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expiry - 60:
            return self._token

        resp = requests.post(
            SETU_TOKEN_URL,
            data={
                "grant_type":    "client_credentials",
                "client_id":     self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token        = data["access_token"]
        self._token_expiry = now + data.get("expires_in", 1800)
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization":         f"Bearer {self._get_token()}",
            "x-product-instance-id": self.product_id,
            "Content-Type":          "application/json",
        }

    # ─────────────────────────────────────────
    # STEP 1 — CREATE CONSENT
    # ─────────────────────────────────────────

    def initiate_consent(self, phone_number: str, redirect_url: str = "http://localhost:3000/callback") -> dict:
        now     = datetime.datetime.utcnow()
        start   = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        expiry  = (now + datetime.timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        fi_from = (now - datetime.timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        fi_to   = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        payload = {
            "ver":       "2.1.0",
            "timestamp": start,
            "txnid":     str(uuid.uuid4()),
            "ConsentDetail": {
                "consentStart":  start,
                "consentExpiry": expiry,
                "consentMode":   "STORE",
                "fetchType":     "PERIODIC",
                "consentTypes":  ["PROFILE", "SUMMARY", "TRANSACTIONS"],
                "fiTypes":       ["DEPOSIT"],
                "DataConsumer":  {"id": self.product_id, "type": "FIU"},
                "Customer": {
                    "id": f"{phone_number}@setu",
                    "Identifiers": [{"type": "MOBILE", "value": phone_number}]
                },
                "Purpose": {
                    "code":   "101",
                    "refUri": "https://api.rebit.org.in/aa/purpose/101.xml",
                    "text":   "Credit scoring via alternative data",
                    "Category": {"type": "string"}
                },
                "FIDataRange": {"from": fi_from, "to": fi_to},
                "DataLife":    {"unit": "MONTH",  "value": 1},
                "Frequency":   {"unit": "MONTH",  "value": 1},
            },
            "redirectUrl": redirect_url,
        }

        resp = requests.post(
            f"{self.base_url}/consents",
            json=payload,
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        return {
            "consent_id":   data.get("id") or data.get("consentHandle"),
            "redirect_url": data.get("url") or data.get("redirectUrl"),
            "raw":          data,
        }

    # ─────────────────────────────────────────
    # STEP 2 — FETCH FI DATA (with polling)
    # ─────────────────────────────────────────

    def fetch_fi_data(self, consent_id: str) -> dict:
        now     = datetime.datetime.utcnow()
        fi_from = (now - datetime.timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        fi_to   = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        session_resp = requests.post(
            f"{self.base_url}/sessions",
            json={
                "ver":       "2.1.0",
                "timestamp": fi_to,
                "txnid":     str(uuid.uuid4()),
                "consentId": consent_id,
                "DataRange": {"from": fi_from, "to": fi_to},
                "format":    "json",
            },
            headers=self._headers(),
            timeout=15,
        )
        session_resp.raise_for_status()
        session_data = session_resp.json()
        session_id   = session_data.get("id") or session_data.get("sessionId")

        if not session_id:
            raise ValueError(f"No session ID from Setu: {session_data}")

        for _ in range(POLL_RETRIES):
            time.sleep(POLL_INTERVAL_S)
            status_resp = requests.get(
                f"{self.base_url}/sessions/{session_id}",
                headers=self._headers(),
                timeout=15,
            )
            status_resp.raise_for_status()
            status_data = status_resp.json()
            status      = status_data.get("status", "PENDING")

            if status == "COMPLETED":
                return self._parse_fi_response(status_data)
            elif status in ("FAILED", "EXPIRED"):
                raise RuntimeError(f"Setu session {session_id} status: {status}")

        raise TimeoutError(f"Setu session {session_id} timed out after {POLL_RETRIES} retries")

    # ─────────────────────────────────────────
    # PARSER — Setu → feature_engine format
    # ─────────────────────────────────────────

    def _parse_fi_response(self, data: dict) -> dict:
        transactions  = []
        profile_hints = {}
        raw_accounts  = []

        accounts = (
            data.get("FI", []) or
            data.get("fiObjects", []) or
            data.get("Payload", {}).get("fiObjects", []) or
            []
        )

        for account in accounts:
            raw_accounts.append(account)

            summary = account.get("Summary", {}) or account.get("summary", {})
            if summary:
                profile_hints["account_type"]    = summary.get("type", "SAVINGS")
                profile_hints["current_balance"]  = float(summary.get("currentBalance", 0) or 0)

            holder      = account.get("Profile", {}) or account.get("profile", {})
            holders     = holder.get("Holders", {}) or holder.get("holders", {})
            holder_list = holders.get("Holder", []) or holders.get("holder", [])
            if holder_list:
                h = holder_list[0] if isinstance(holder_list, list) else holder_list
                profile_hints["name"]   = h.get("name", "")
                profile_hints["mobile"] = h.get("mobile", "")

            tx_wrapper = account.get("Transactions", {}) or account.get("transactions", {})
            tx_list    = (
                tx_wrapper.get("Transaction", []) or
                tx_wrapper.get("transaction", []) or
                []
            )

            for tx in tx_list:
                try:
                    tx_type = str(tx.get("type", tx.get("txnType", "DEBIT"))).upper()
                    if tx_type in ("CR", "C"): tx_type = "CREDIT"
                    elif tx_type in ("DR", "D"): tx_type = "DEBIT"

                    transactions.append({
                        "date":      tx.get("valueDate") or tx.get("transactionTimestamp", "")[:10],
                        "amount":    abs(float(tx.get("amount", 0) or 0)),
                        "type":      tx_type,
                        "narration": str(tx.get("narration") or tx.get("remarks") or ""),
                        "balance":   float(tx.get("currentBalance", 0) or 0),
                    })
                except Exception:
                    continue

        return {
            "transactions":  transactions,
            "profile_hints": profile_hints,
            "raw_accounts":  raw_accounts,
        }

    # ─────────────────────────────────────────
    # CONSENT STATUS
    # ─────────────────────────────────────────

    def get_consent_status(self, consent_id: str) -> str:
        resp = requests.get(
            f"{self.base_url}/consents/{consent_id}",
            headers=self._headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("status", "UNKNOWN")
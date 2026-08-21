"""Extract credit features from BC agent transaction data."""
from datetime import datetime


def extract(bc_data: dict) -> dict:
    transactions = bc_data.get("transactions", [])
    if not transactions:
        return {"data_source_bc_agent": True}

    first_txn = datetime.strptime(bc_data["first_transaction_date"], "%Y-%m-%d")
    as_of = datetime.strptime(bc_data["data_as_of"], "%Y-%m-%d")
    months = max(1, (as_of - first_txn).days / 30)

    deposits = [t for t in transactions if t["type"] == "CASH_DEPOSIT"]
    withdrawals = [t for t in transactions if t["type"] in ("CASH_WITHDRAWAL", "MICRO_ATM")]

    # emergency_buffer_months
    balances = [t["balance_after"] for t in transactions]
    avg_balance = sum(balances) / len(balances) if balances else 0
    total_deps = sum(d["amount"] for d in deposits)
    avg_monthly_dep = total_deps / months
    ebm = round(min(6.0, max(0, avg_balance / (avg_monthly_dep / 30 + 1))), 4)

    # cash_withdrawal_dependency
    total_wd = sum(w["amount"] for w in withdrawals)
    if total_deps == 0:
        cwd = 0.8
    else:
        cwd = round(min(1.0, max(0, total_wd / total_deps)), 4)

    # bounced_transaction_count (negative balance events)
    neg_events = sum(1 for t in transactions if t["balance_after"] < 0)
    btc = min(10, neg_events)

    # eod_balance_volatility
    if len(balances) < 3:
        ebv = 0.5
    else:
        m = sum(balances) / len(balances)
        std = (sum((b - m) ** 2 for b in balances) / len(balances)) ** 0.5
        ebv = round(min(1.0, max(0, std / (m + 1))), 4)

    # identity_device_mismatch from field verification
    fv = bc_data.get("field_verification", {})
    if fv.get("verified") is False:
        idm = 1
    elif fv.get("shop_exists") is False:
        idm = 1
    else:
        idm = 0

    return {
        "emergency_buffer_months": ebm,
        "cash_withdrawal_dependency": cwd,
        "bounced_transaction_count": btc,
        "eod_balance_volatility": ebv,
        "identity_device_mismatch": idm,
        "data_source_bc_agent": True,
    }

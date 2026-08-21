"""FastAPI application for PDR scoring pipeline.
Endpoints: POST /score, GET /health, GET /demo/{user_id}
           + full Setu AA integration endpoints
"""

from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from middleman_scorer import score_middleman_user
import uvicorn
import json
import datetime
import pathlib
import os
from scorer import score_user, ntc_model, msme_model, ALTERNATIVE_PRODUCTS
from setu_handler import SetuAAHandler

# ─────────────────────────────────────────────
# REQUEST MODELS
# ─────────────────────────────────────────────

class ScoreRequest(BaseModel):
    user_profile: dict
    transactions: list
    gst_data: dict

class AAScoreRequest(BaseModel):
    user_id: str
    consent_id: Optional[str] = None

class SetuConsentRequest(BaseModel):
    phone_number: str
    is_msme: int = 0
    academic_background_tier: int = 2
    purpose_of_loan_encoded: int = 1
    business_vintage_months: int = 24
    gst_filing_consistency_score: int = 6
    telecom_number_vintage_days: int = 365

class SetuScoreRequest(BaseModel):
    consent_id: str
    is_msme: int = 0
    academic_background_tier: int = 2
    purpose_of_loan_encoded: int = 1
    business_vintage_months: int = 24
    gst_filing_consistency_score: int = 6
    telecom_number_vintage_days: int = 365

class DeclinedRequest(BaseModel):
    """Request from a partner bank for a previously declined applicant."""
    applicant_name: str
    bank_rejection_reason: str = 'Insufficient credit history'
    monthly_income: Optional[float] = None
    loan_amount_requested: Optional[float] = None
    user_profile: Optional[Dict[str, Any]] = None
    transactions: Optional[list] = None
    gst_data: Optional[Dict[str, Any]] = None

class MiddlemanScoreRequest(BaseModel):
    supplierdata: Optional[Dict[str, Any]] = None
    gstdata: Optional[Dict[str, Any]] = None
    telecomdata: Optional[Dict[str, Any]] = None
    utilitydata: Optional[Dict[str, Any]] = None
    bcagentdata: Optional[Dict[str, Any]] = None
    applicantmetadata: Dict[str, Any]

class ChatbotRequest(BaseModel):
    query: str

class ManagerStatusUpdate(BaseModel):
    outcome: str
    remarks: str

# ─────────────────────────────────────────────
# APP + MIDDLEWARE
# ─────────────────────────────────────────────

app = FastAPI(title='FintrixAi Credit Scoring API', version='2.0.0')
CHATBOT_DB = str(pathlib.Path(__file__).parent / "applicant_cards.db")

@app.on_event("startup")
def seed_chatbot_db():
    """Re-seed applicant_cards.db from demo_users.json on every startup.
    This ensures any edits to demo profiles (e.g. Arjun Sharma) are reflected
    automatically — no need to manually run build_applicant_cards.py.
    """
    try:
        from build_applicant_cards import build_cards
        build_cards(pathlib.Path(CHATBOT_DB))
        print("[STARTUP] applicant_cards.db seeded from demo_users.json")
    except Exception as e:
        print(f"[STARTUP WARN] Could not seed chatbot DB: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)

# ─────────────────────────────────────────────
# SETU CLIENT (singleton)
# ─────────────────────────────────────────────

setu = SetuAAHandler(
    client_id     = os.environ.get("SETU_CLIENT_ID",     "5cd97a89-ad5d-41a6-91b6-07887d7dc6e0"),
    client_secret = os.environ.get("SETU_CLIENT_SECRET", "MVUbfZP217ZSgDhKfNbtw1NuPCTRgq0t"),
    product_id    = os.environ.get("SETU_PRODUCT_ID",    "50854c6e-589c-43cb-bdb7-a276cd56086c"),
)

# ─────────────────────────────────────────────
# DEMO USER HELPERS
# ─────────────────────────────────────────────

def load_demo_users() -> list:
    path = pathlib.Path(__file__).parent / 'demo_users.json'
    try:
        return json.loads(path.read_text(encoding='utf-8'))['demo_users']
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read demo_users.json: {e}")

def find_user(user_id: str) -> Optional[dict]:
    return next(
        (u for u in load_demo_users() if u['user_id'] == user_id),
        None
    )

def _account_summary(transactions: list) -> dict:
    """Reusable transaction summary block."""
    if not transactions:
        return {
            "total_transactions": 0,
            "date_range_from": None,
            "date_range_to": None,
            "total_credits": 0.0,
            "total_debits": 0.0,
            "closing_balance": 0.0,
        }
    total_tx      = len(transactions)
    date_from     = min(t['date'] for t in transactions if 'date' in t)
    date_to       = max(t['date'] for t in transactions if 'date' in t)
    total_credits = round(sum(float(t['amount']) for t in transactions if t.get('type') == 'CREDIT'), 2)
    total_debits  = round(sum(abs(float(t['amount'])) for t in transactions if t.get('type') == 'DEBIT'), 2)
    sorted_tx     = sorted(transactions, key=lambda x: x.get('date', ''))
    closing_bal   = round(float(sorted_tx[-1].get('balance', 0)), 2)
    return {
        "total_transactions": total_tx,
        "date_range_from":    date_from,
        "date_range_to":      date_to,
        "total_credits":      total_credits,
        "total_debits":       total_debits,
        "closing_balance":    closing_bal,
    }

# ─────────────────────────────────────────────
# CORE ENDPOINTS
# ─────────────────────────────────────────────

@app.post('/score')
def score_endpoint(req: ScoreRequest):
    try:
        result = score_user(req.transactions, req.user_profile, req.gst_data)
        print(f"[SCORE] {req.user_profile.get('name','unknown')} -> {result['grade']}")

        # Auto-save to chatbot DB so the loan officer can query it immediately
        try:
            import time
            from context_layer import init_database, save_applicant_card
            init_database(CHATBOT_DB)
            applicant_id = (
                req.user_profile.get("applicant_id")
                or req.user_profile.get("user_id")
                or f"app_{int(time.time())}"
            )
            save_applicant_card(
                db_path=CHATBOT_DB,
                scoring_result=result,
                applicant_id=applicant_id,
                name=req.user_profile.get("name", "Unknown"),
                city=req.user_profile.get("city", ""),
                business_type=req.user_profile.get("business_type", ""),
            )
            result["applicant_id"] = applicant_id
            print(f"[CHATBOT-DB] Saved {applicant_id} to applicant_cards.db")
        except Exception as db_err:
            print(f"[WARN] Could not auto-save to chatbot DB: {db_err}")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/score/declined')
def declined_endpoint(req: DeclinedRequest):
    """B2B endpoint: partner bank submits a declined applicant for alternative scoring.

    If transactions + profile are provided, runs full PDR scoring and returns
    the PDR grade alongside alternative product recommendations.
    If no transaction data is available, returns generic alternative products only.
    """
    try:
        if req.transactions and req.user_profile:
            result = score_user(
                req.transactions,
                req.user_profile,
                req.gst_data or {'available': False},
            )
            pdr_grade = result['grade']
            loan_offer = result.get('loan_offer', {})
            default_prob = result.get('default_probability')
            decision_source = result.get('decision_source', 'model')
        else:
            # No data — return generic alternative products
            pdr_grade = None
            loan_offer = {}
            default_prob = None
            decision_source = 'no_data'

        # Determine which alternative products to surface
        if pdr_grade in ('A', 'B', 'C'):
            # FintrixAi approves where the bank declined — full loan offer
            alternative_path = {
                'pdr_outcome': 'FINTRIXAI APPROVED',
                'pdr_grade': pdr_grade,
                'loan_offer': loan_offer,
                'alternative_products': [],
                'message': f'FintrixAi scores this applicant as Grade {pdr_grade}. Standard lending may be available.',
            }
        else:
            # Both FintrixAi and bank decline — surface micro-products
            alternative_path = {
                'pdr_outcome': 'FINTRIXAI DECLINED — Alternative Path',
                'pdr_grade': pdr_grade,
                'loan_offer': {},
                'alternative_products': ALTERNATIVE_PRODUCTS,
                'message': 'Conventional lending declined. The following alternative financial products may be suitable.',
            }

        print(f"[DECLINED] {req.applicant_name} bank_reason='{req.bank_rejection_reason}' pdr_grade={pdr_grade}")
        return {
            'applicant_name': req.applicant_name,
            'bank_rejection_reason': req.bank_rejection_reason,
            'default_probability': default_prob,
            'decision_source': decision_source,
            'alternative_path': alternative_path,
            'scored_at': datetime.datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/health')
def health_endpoint():
    return {
        'status':       'ok',
        'model_loaded': ntc_model is not None and msme_model is not None,
        'setu_ready':   True,
        'timestamp':    datetime.datetime.now().isoformat()
    }

@app.get('/demo/{user_id}')
def demo_endpoint(user_id: str):
    demo_path = pathlib.Path(__file__).parent / 'demo_users.json'
    try:
        data = json.loads(demo_path.read_text(encoding='utf-8'))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading demo users: {e}")

    user = next((u for u in data['demo_users'] if u['user_id'] == user_id), None)
    if not user:
        raise HTTPException(404, f'{user_id} not found')

    result = score_user(user['transactions'], user['user_profile'], user['gst_data'])
    result['persona']        = user['persona']
    result['expected_grade'] = user['expected_grade']
    result['user_id']        = user_id
    result['profile']        = user['user_profile']

    print(f"[DEMO] {user_id} ({user['persona']}) -> {result['grade']} expected {user['expected_grade']}")
    return result

# ─────────────────────────────────────────────
# MIDDLEMAN ENDPOINTS
# ─────────────────────────────────────────────

@app.post('/score/middleman')
def score_middleman_endpoint(req: MiddlemanScoreRequest):
    try:
        result = score_middleman_user(
            applicantmetadata=req.applicantmetadata,
            supplierdata=req.supplierdata,
            gstdata=req.gstdata,
            telecomdata=req.telecomdata,
            utilitydata=req.utilitydata,
            bcagentdata=req.bcagentdata
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/middleman/data/{msme_id}/{source}')
def get_middleman_data(msme_id: str, source: str):
    valid_sources = ["supplier", "gst", "telecom", "utility", "bcagent"]
    if source not in valid_sources:
        raise HTTPException(status_code=400, detail="Invalid source")
    
    # Hardcoded sample payload per source for demo purposes
    demo_data = {
        "supplier": {"invoices_cleared": 10, "avg_payment_days": 15},
        "gst": {"filing_consistency": 8, "turnover": 500000},
        "telecom": {"vintage_days": 400, "recharge_drop_ratio": 0.1},
        "utility": {"electricity_on_time": 0.95, "avg_dpd": 2},
        "bcagent": {"cash_deposited": 100000, "active_days": 25}
    }
    
    return {source: demo_data[source]}

@app.get('/middleman/consent/{msme_id}')
def get_middleman_consent(msme_id: str):
    return {
        "msme_id": msme_id,
        "consents": [
            {"source": "supplier", "consent_granted": True},
            {"source": "gst", "consent_granted": True},
            {"source": "telecom", "consent_granted": True},
            {"source": "utility", "consent_granted": True},
            {"source": "bcagent", "consent_granted": True}
        ]
    }

# ═══════════════════════════════════════════════════
# SIMULATED AA LAYER (demo_users.json personas)
# ═══════════════════════════════════════════════════

@app.get('/aa/health')
def aa_health_endpoint():
    return {
        "aa_status":       "operational",
        "fip_id":          "FINTRIXAI-DEMO-FIP",
        "fip_name":        "FintrixAi Demo Financial Information Provider",
        "aa_version":      "1.0",
        "users_available": len(load_demo_users()),
        "endpoints": [
            "GET  /aa/users",
            "POST /aa/users/{user_id}/consent",
            "GET  /aa/users/{user_id}/profile",
            "GET  /aa/users/{user_id}/statements",
            "POST /aa/score"
        ],
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get('/aa/users')
def aa_users_endpoint():
    users = load_demo_users()
    summaries = []
    for u in users:
        profile     = u.get('user_profile', {})
        persona_type = u.get('model', 'NTC')
        summaries.append({
            "user_id":       u.get("user_id"),
            "name":          profile.get("name", "Unknown"),
            "persona":       u.get("persona", "Unknown"),
            "city":          profile.get("city", "Unknown"),
            "business_type": profile.get("business_type", ""),
            "persona_type":  persona_type
        })
    print(f"[AA] /aa/users — returned {len(summaries)} user summaries")
    return {
        "aa_version": "1.0",
        "fip_id":     "PDR-DEMO-FIP",
        "users":      summaries,
        "total":      len(summaries)
    }

@app.post('/aa/users/{user_id}/consent')
def aa_consent_endpoint(user_id: str, body: dict = None):
    user = find_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found in FIP")

    timestamp  = int(datetime.datetime.now().timestamp())
    consent_id = f"CONSENT-{user_id}-{timestamp}"
    granted_at = datetime.datetime.now()
    expires_at = granted_at + datetime.timedelta(hours=24)
    print(f"[AA] Consent granted for {user_id}")
    return {
        "consent_id":  consent_id,
        "user_id":     user_id,
        "status":      "GRANTED",
        "granted_at":  granted_at.isoformat(),
        "expires_at":  expires_at.isoformat(),
        "data_access": ["TRANSACTIONS", "PROFILE", "GST"],
        "fip_id":      "PDR-DEMO-FIP",
        "message":     "Consent granted. Financial data access authorised for 24 hours."
    }

@app.get('/aa/users/{user_id}/profile')
def aa_profile_endpoint(user_id: str):
    user = find_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found in FIP")

    profile = user.get("user_profile", {})
    print(f"[AA] Profile data fetched for {user_id}")
    return {
        "aa_version": "1.0",
        "user_id":    user_id,
        "fip_id":     "PDR-DEMO-FIP",
        "data_type":  "PROFILE",
        "profile": {
            "name":                       profile.get("name"),
            "city":                       profile.get("city"),
            "business_type":              profile.get("business_type"),
            "business_vintage_months":    profile.get("business_vintage_months"),
            "academic_background_tier":   profile.get("academic_background_tier"),
            "purpose_of_loan_encoded":    profile.get("purpose_of_loan_encoded"),
            "telecom_number_vintage_days": profile.get("telecom_number_vintage_days"),
            "gst_filing_consistency_score": profile.get("gst_filing_consistency_score")
        },
        "gst_data":   user.get("gst_data", {}),
        "fetched_at": datetime.datetime.now().isoformat()
    }

@app.get('/aa/users/{user_id}/statements')
def aa_statements_endpoint(user_id: str):
    user = find_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found in FIP")

    transactions = user.get("transactions", [])
    print(f"[AA] Statement data fetched for {user_id} — {len(transactions)} transactions")
    return {
        "aa_version":      "1.0",
        "user_id":         user_id,
        "fip_id":          "PDR-DEMO-FIP",
        "data_type":       "BANK_STATEMENTS",
        "account_summary": _account_summary(transactions),
        "transactions":    transactions,
        "fetched_at":      datetime.datetime.now().isoformat()
    }

@app.post('/aa/score')
def aa_score_endpoint(req: AAScoreRequest):
    user = find_user(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {req.user_id} not found in FIP")

    transactions = user.get("transactions", [])
    user_profile = user.get("user_profile", {})
    gst_data     = user.get("gst_data", {})
    result       = score_user(transactions, user_profile, gst_data)
    grade        = result.get('grade')

    print(f"[AA] Full AA score for {req.user_id} ({user_profile.get('name')}) -> {grade}")
    return {
        "aa_version":      "1.0",
        "fip_id":          "PDR-DEMO-FIP",
        "user_id":         req.user_id,
        "persona":         user.get("persona"),
        "consent_id":      req.consent_id or "DEMO-NO-CONSENT",
        "account_summary": _account_summary(transactions),
        "scoring_result":  result,
        "scored_at":       datetime.datetime.now().isoformat(),
        "message":         f"FintrixAi scoring complete for {user_profile.get('name')}. Grade: {grade}."
    }

# ═══════════════════════════════════════════════════
# REAL SETU AA INTEGRATION
# Uses live Setu sandbox credentials.
# Flow: POST /setu/consent → user approves → POST /setu/score
# ═══════════════════════════════════════════════════

@app.post('/setu/consent')
def setu_consent_endpoint(req: SetuConsentRequest):
    """Step 1: Create a real Setu AA consent request.
    Frontend redirects user to the returned redirect_url.
    After approval, Setu redirects to localhost:3000/callback?consent_id=...
    """
    try:
        result = setu.initiate_consent(req.phone_number)
        print(f"[SETU] Consent created for {req.phone_number} → {result['consent_id']}")
        return {
            "consent_id":   result["consent_id"],
            "redirect_url": result["redirect_url"],
            "message":      "Redirect user to redirect_url to approve consent on Setu",
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Setu consent creation failed: {e}")


@app.post('/setu/score')
def setu_score_endpoint(req: SetuScoreRequest):
    """Step 2: After user approves consent, fetch real FI data and score.
    Frontend calls this from /callback page with consent_id from URL params.
    """
    try:
        fi           = setu.fetch_fi_data(req.consent_id)
        transactions = fi["transactions"]
        profile_hints = fi["profile_hints"]

        print(f"[SETU] Fetched {len(transactions)} transactions for consent {req.consent_id}")

        profile = {
            "is_msme":                      req.is_msme,
            "academic_background_tier":     req.academic_background_tier,
            "purpose_of_loan_encoded":      req.purpose_of_loan_encoded,
            "business_vintage_months":      req.business_vintage_months,
            "gst_filing_consistency_score": req.gst_filing_consistency_score,
            "telecom_number_vintage_days":  req.telecom_number_vintage_days,
            "name": profile_hints.get("name", "Applicant"),
        }

        gst_data = {"available": False}
        result   = score_user(transactions, profile, gst_data)

        print(f"[SETU] Score for {profile['name']}: {result['grade']} (PD={result['default_probability']})")
        return {
            "consent_id":        req.consent_id,
            "name":              profile["name"],
            "transaction_count": len(transactions),
            "account_summary":   _account_summary(transactions),
            "scoring_result":    result,
            "data_source":       "setu_aa_sandbox",
            "scored_at":         datetime.datetime.now().isoformat(),
        }

    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Setu scoring failed: {e}")


@app.get('/setu/consent/{consent_id}/status')
def setu_consent_status(consent_id: str):
    """Optional: check consent approval status before attempting FI fetch."""
    try:
        status = setu.get_consent_status(consent_id)
        return {"consent_id": consent_id, "status": status}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ═══════════════════════════════════════════════════
# CHATBOT ENDPOINTS
# ═══════════════════════════════════════════════════

@app.post('/chatbot/ask')
def chatbot_ask(req: ChatbotRequest):
    """
    Plain-English question from a loan officer.
    Returns a structured, formatted response with LLM explanation from Ollama.
    """
    try:
        from chatbot_router import route_query
        from chatbot_context import build_prompt, fetch_applicant_context
        from llm_client import call_ollama, get_ollama_status
        from response_formatter import format_response

        routed = route_query(req.query)
        system_prompt, user_prompt = build_prompt(routed, CHATBOT_DB)
        response_text = call_ollama(system_prompt, user_prompt, query_type=routed.query_type.value)

        ctx = None
        ctx_b = None
        if routed.applicant_ids:
            ctx = fetch_applicant_context(CHATBOT_DB, routed.applicant_ids[0])
        if len(routed.applicant_ids) > 1:
            ctx_b = fetch_applicant_context(CHATBOT_DB, routed.applicant_ids[1])

        formatted = format_response(routed.query_type, response_text, ctx, ctx_b)
        ollama_info = get_ollama_status()
        return {
            "status":        "success",
            "query_type":    routed.query_type.value,
            "applicant_ids": routed.applicant_ids,
            "message":       formatted,
            "ollama_info":   ollama_info,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/chatbot/ollama/status')
def chatbot_ollama_status():
    """Returns status of local Ollama LLM service and active model."""
    from llm_client import get_ollama_status
    return get_ollama_status()


class OllamaModelRequest(BaseModel):
    model: str


@app.post('/chatbot/ollama/model')
def set_ollama_model(req: OllamaModelRequest):
    """Dynamically set active Ollama model (e.g. llama3:latest)."""
    from llm_client import set_active_model, get_ollama_status
    set_active_model(req.model)
    return {"status": "success", "ollama_info": get_ollama_status()}


@app.get('/chatbot/search')
def chatbot_search(grade: str = None, decision: str = None, limit: int = 10):
    """Search applicants by grade or decision. E.g. /chatbot/search?grade=E"""
    try:
        from context_layer import search_applicants
        filters: dict = {}
        if grade:
            filters["grade"] = grade.upper()
        if decision:
            filters["decision"] = decision.upper()
        results = search_applicants(CHATBOT_DB, filters)[:limit]
        return {"status": "success", "count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/chatbot/stats')
def chatbot_stats():
    """Portfolio-level statistics: grade distribution, averages, recent applicants."""
    try:
        from context_layer import get_statistics
        stats = get_statistics(CHATBOT_DB)
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────
# DASHBOARD ENDPOINTS
# ─────────────────────────────────────────────

@app.get('/api/manager/applicants')
def get_all_applicants():
    try:
        from context_layer import search_applicants
        return search_applicants(CHATBOT_DB, {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put('/api/manager/applicant/{applicant_id}/status')
def update_status(applicant_id: str, req: ManagerStatusUpdate):
    try:
        from context_layer import update_applicant_status
        update_applicant_status(CHATBOT_DB, applicant_id, req.outcome, req.remarks)
        return {"status": "success", "message": f"Updated {applicant_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/user/status/{applicant_id}')
def get_user_status(applicant_id: str):
    from context_layer import fetch_applicant_status
    status = fetch_applicant_status(CHATBOT_DB, applicant_id)
    if not status:
        raise HTTPException(status_code=404, detail="Applicant not found")
    return status

if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)
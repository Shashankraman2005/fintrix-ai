"""Main scoring orchestrator for FintrixAi.
Loads NTC and MSME XGBoost models at module level.
Pipeline: feature_engine -> pre_layer -> model -> SHAP -> output.
"""
import pathlib
import numpy as np
import pandas as pd
try:
    import shap
except ImportError:
    import os
    os.system('pip install shap')
    import shap
import joblib
from feature_engine import compute_features
from pre_layer import apply_pre_layer

# ─────────────────────────────────────────────
# MODEL LOADING
# ─────────────────────────────────────────────

_base = pathlib.Path(__file__).parent

def _load(filename):
    p = _base / filename
    try:
        obj = joblib.load(p)
        print(f"[OK] Loaded {filename}")
        return obj
    except Exception as e:
        print(f"[ERROR] Failed to load {filename}: {e}")
        return None

ntc_model  = _load('ntc_model/models/ntc_credit_model.pkl')
msme_model = _load('msme_model/models/xgb_msme_raw.pkl')  # raw XGB — avoids PlattCalibratedModel pickle error

# ─────────────────────────────────────────────
# FEATURE LISTS — derived from trained model (never hardcoded)
# ─────────────────────────────────────────────

if ntc_model is not None:
    try:
        NTC_FEATURES = list(ntc_model.feature_names_in_)
    except AttributeError:
        try:
            NTC_FEATURES = ntc_model.get_booster().feature_names
        except Exception:
            NTC_FEATURES = []
else:
    NTC_FEATURES = []

if msme_model is not None:
    try:
        MSME_FEATURES = list(msme_model.feature_names_in_)
    except AttributeError:
        MSME_FEATURES = [str(f) for f in msme_model.get_booster().feature_names]
else:
    MSME_FEATURES = []

# ─────────────────────────────────────────────
# BUILD SHAP EXPLAINERS — expensive, do once at load time
# ─────────────────────────────────────────────

if ntc_model is not None:
    try:
        _ntc_base = None
        if hasattr(ntc_model, 'calibrated_classifiers_') and len(ntc_model.calibrated_classifiers_) > 0:
            _sub = ntc_model.calibrated_classifiers_[0].estimator
            if hasattr(_sub, 'named_steps'):
                _ntc_base = _sub.named_steps.get('rf', _sub)
            else:
                _ntc_base = _sub
        else:
            _ntc_base = ntc_model

        if _ntc_base is not None:
            ntc_explainer = shap.TreeExplainer(_ntc_base)
        else:
            ntc_explainer = None
    except Exception as _e:
        print(f"[WARN] NTC SHAP explainer initialization fallback: {_e}")
        ntc_explainer = None
else:
    ntc_explainer = None

if msme_model is not None:
    try:
        msme_explainer = shap.TreeExplainer(msme_model)
    except Exception as _e:
        print(f"[WARN] MSME SHAP explainer initialization fallback: {_e}")
        msme_explainer = None
else:
    msme_explainer = None

# ─────────────────────────────────────────────
# HUMAN-READABLE REASON MAP
# ─────────────────────────────────────────────

SHAP_REASON_MAP = {
    'utility_payment_consistency':   'Utility bill payment discipline',
    'avg_utility_dpd':               'Utility payment timeliness',
    'rent_wallet_share':             'Rent as share of income',
    'subscription_commitment_ratio': 'Subscription payment commitment',
    'emergency_buffer_months':       'Emergency savings buffer',
    'min_balance_violation_count':   'Minimum balance violations',
    'eod_balance_volatility':        'Account balance stability',
    'essential_vs_lifestyle_ratio':  'Essential vs lifestyle spending',
    'cash_withdrawal_dependency':    'Cash withdrawal dependency',
    'bounced_transaction_count':     'Bounce charges on account',
    'telecom_number_vintage_days':   'SIM card age - identity stability',
    'telecom_recharge_drop_ratio':   'Telecom recharge consistency',
    'academic_background_tier':      'Educational background tier',
    'purpose_of_loan_encoded':       'Stated loan purpose',
    'employment_vintage_days':       'Employment tenure',
    'business_vintage_months':       'Business operating history',
    'revenue_growth_trend':          'Revenue growth trajectory',
    'revenue_seasonality_index':     'Revenue seasonality pattern',
    'operating_cashflow_ratio':      'Operating cashflow health',
    'cashflow_volatility':           'Monthly cashflow volatility',
    'customer_concentration_ratio':  'Customer concentration risk',
    'gst_filing_consistency_score':  'GST filing regularity',
    'monthly_income':                'Monthly income level',
    'avg_invoice_payment_delay':     'Invoice payment delay',
    'repeat_customer_revenue_pct':   'Repeat customer revenue share',
    'vendor_payment_discipline':     'Vendor payment reliability',
    'gst_to_bank_variance':          'GST declared vs actual turnover',
    'p2p_circular_loop_flag':        'Circular fund flow detected',
    'benford_anomaly_score':         'Transaction amount anomaly',
    'round_number_spike_ratio':      'Round number transaction spike',
    'turnover_inflation_spike':      'Turnover inflation indicator',
    'identity_device_mismatch':      'Identity verification signal',
}

GRADE_THRESHOLDS = [
    (0.05, 'A', 'APPROVED'),
    (0.15, 'B', 'APPROVED WITH CONDITIONS'),
    (0.30, 'C', 'MANUAL REVIEW'),
    (0.50, 'D', 'REJECTED'),
    (1.01, 'E', 'REJECTED'),
]

# ─────────────────────────────────────────────
# LOAN POLICY TABLE  (interest rates are illustrative / RBI-compliant ranges)
# ─────────────────────────────────────────────

LOAN_POLICY = {
    'A': {
        'rate_min': 11.0, 'rate_max': 14.0,
        'income_multiplier': 20,
        'tenures': [12, 24, 36, 48, 60],
        'product': 'Prime Personal / Business Loan',
    },
    'B': {
        'rate_min': 14.0, 'rate_max': 20.0,
        'income_multiplier': 12,
        'tenures': [12, 24, 36, 48],
        'product': 'Conditional Loan — Standard NBFC',
    },
    'C': {
        'rate_min': 20.0, 'rate_max': 28.0,
        'income_multiplier': 6,
        'tenures': [12, 24, 36],
        'product': 'High-Risk Loan — Manual Review Required',
    },
}

ALTERNATIVE_PRODUCTS = [
    {
        'name': 'Microfinance Loan (NBFC-MFI)',
        'max_amount': 50000,
        'rate': '24–36% p.a.',
        'detail': 'Small-ticket lending via licensed MFI partners (e.g., Arohan, CreditAccess)',
        'icon': 'groups',
    },
    {
        'name': 'Gold / Asset-Backed Loan',
        'max_amount': 200000,
        'rate': '12–18% p.a.',
        'detail': 'Secured loan against gold jewellery or fixed deposit — lower risk premium',
        'icon': 'toll',
    },
    {
        'name': 'BNPL Credit Line',
        'max_amount': 25000,
        'rate': '0–24% p.a.',
        'detail': 'Buy Now Pay Later via fintech partner network (e.g., LazyPay, Simpl)',
        'icon': 'credit_card',
    },
    {
        'name': 'Self-Help Group (SHG) Loan',
        'max_amount': 20000,
        'rate': '18–24% p.a.',
        'detail': 'Community-backed lending through NABARD-linked SHG networks',
        'icon': 'handshake',
    },
]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _to_row(features: dict, feature_list: list) -> pd.DataFrame:
    """Single-row DataFrame for model input, filling missing cols with 0.
    Adds MSME engineered features and one-hot business_type columns if needed.
    """
    enriched = dict(features)

    # MSME engineered features (computed from base features if missing)
    ocr  = float(enriched.get('operating_cashflow_ratio', 1.0))
    cv   = float(enriched.get('cashflow_volatility', 0.0))
    gtbv = float(enriched.get('gst_to_bank_variance', 0.0))
    gfcs = float(enriched.get('gst_filing_consistency_score', 6.0))
    aipd = float(enriched.get('avg_invoice_payment_delay', 30.0))
    vpd  = float(enriched.get('vendor_payment_discipline', 10.0))

    enriched.setdefault('stress_composite',   max(0.0, 1.0 - ocr) * 0.5 + cv * 0.5)
    enriched.setdefault('gst_risk_score',     max(0.0, gtbv * 0.6 + max(0.0, 1.0 - gfcs / 12) * 0.4))
    enriched.setdefault('wc_pressure',        max(0.0, min(1.0, aipd / 90.0)))
    enriched.setdefault('liquidity_fragility',max(0.0, min(1.0, (vpd / 90.0) * 0.5 + cv * 0.5)))

    # One-hot business_type columns
    biz_type = str(enriched.get('business_type', '')).lower().replace(' ', '_').replace('/', '_')
    for bt in ('agri_seasonal', 'manufacturer', 'retailer_kirana', 'service_provider'):
        enriched.setdefault(f'business_type_{bt}', 1.0 if bt in biz_type else 0.0)

    row = pd.DataFrame([{f: enriched.get(f, 0.0) for f in feature_list}])
    row = row.fillna(0)  # no NaN reaches the model
    return row


def _grade(pd_score: float):
    for threshold, g, o in GRADE_THRESHOLDS:
        if pd_score < threshold:
            return g, o
    return 'E', 'REJECTED'


def _shap_reasons(shap_vals, feature_list: list, top_n: int = 5) -> list[dict]:
    pairs = sorted(zip(shap_vals, feature_list), key=lambda x: abs(x[0]), reverse=True)
    reasons = []
    for val, feat in pairs[:top_n]:
        abs_val = abs(val)
        reasons.append({
            'feature': feat,
            'reason': SHAP_REASON_MAP.get(feat, feat),
            'shap_value': round(float(val), 4),
            'direction': 'risk' if val > 0 else 'strength',
            'impact': (
                'Very High' if abs_val > 0.3 else
                'High'      if abs_val > 0.15 else
                'Medium'
            ),
        })
    return reasons


def _loan_offer(grade: str, features: dict) -> dict:
    """Compute grade-based loan offer or alternative products for rejected applicants."""
    if grade in ('D', 'E'):
        return {
            'eligible': False,
            'reason': 'Credit profile does not meet minimum lending criteria.',
            'alternative_products': ALTERNATIVE_PRODUCTS,
        }

    policy = LOAN_POLICY[grade]
    monthly_income = float(features.get('monthly_income', 0))

    # MSME: estimate monthly surplus from cashflow ratio if no direct income
    if monthly_income <= 0:
        ocr = float(features.get('operating_cashflow_ratio', 1.0))
        # Rough proxy — 0.1 above 1.0 OCR represents ≈₹10k monthly surplus headroom
        # We cannot reliably compute max_loan without actual revenue, so leave as None
        monthly_income = 0

    max_loan = round(monthly_income * policy['income_multiplier']) if monthly_income > 0 else None

    return {
        'eligible': True,
        'interest_rate_min': policy['rate_min'],
        'interest_rate_max': policy['rate_max'],
        'interest_rate_display': f"{policy['rate_min']}–{policy['rate_max']}% p.a.",
        'max_loan_amount': max_loan,
        'tenure_options_months': policy['tenures'],
        'recommended_product': policy['product'],
        'alternative_products': [],
    }


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def score_user(
    transactions: list[dict],
    profile: dict,
    gst_data: dict
) -> dict:
    """Score a user through the FintrixAi pipeline.

    Routes on profile['business_vintage_months'] and profile['business_type']:
      - NTC: business_vintage_months == 0 or business_type == 'Individual / NTC'
      - MSME: all others
    Both routed 100% to XGBoost (no CatBoost ensemble).
    """
    # ── 1. Feature computation ────────────────────────────────────────────
    features = compute_features(transactions, profile, gst_data)

    # ── 2. Pre-layer (hard rules) ─────────────────────────────────────────
    pre_result = apply_pre_layer(features)

    if pre_result is not None:
        grade, outcome, reason = pre_result
        # Build a normalized shap_breakdown of zeros for pre-layer decisions
        feat_names = NTC_FEATURES if NTC_FEATURES else MSME_FEATURES
        shap_breakdown = {f: 0.0 for f in feat_names}
        return {
            'grade': grade,
            'outcome': outcome,
            'default_probability': None,
            'decision_source': 'pre_layer',
            'primary_reason': reason,
            'shap_reasons': [],
            'shap_breakdown': shap_breakdown,
            'features': features,
            'loan_offer': _loan_offer(grade, features),
        }

    # ── 3. Routing — NTC vs MSME ──────────────────────────────────────────
    is_ntc = (
        profile.get('business_vintage_months', 0) == 0
        or profile.get('business_type') == 'Individual / NTC'
    )

    if is_ntc:
        if ntc_model is None:
            raise RuntimeError('NTC model not loaded — run train.py first')
        model = ntc_model
        feature_list = NTC_FEATURES
        explainer = ntc_explainer
    else:
        if msme_model is None:
            raise RuntimeError('MSME model not loaded — run train.py first')
        model = msme_model
        feature_list = MSME_FEATURES
        explainer = msme_explainer

    # ── 4. Build feature row — fillna(0) ensures no NaN ───────────────────
    features_df = _to_row(features, feature_list)

    # Guarantee: no NaN reaches the model
    assert features_df.isna().sum().sum() == 0, "NaN values detected before model input!"

    # ── 5. Model scoring (100% XGBoost, no ensemble) ──────────────────────
    pd_score = float(model.predict_proba(features_df)[0][1])

    # ── 6. SHAP explanation ───────────────────────────────────────────────
    shap_values = explainer.shap_values(features_df)

    # Handle multi-class shape: (2, 1, n) — use positive class
    if isinstance(shap_values, list):
        shap_vals = shap_values[1][0] if len(shap_values) == 2 else shap_values[0]
    elif len(shap_values.shape) == 3:
        shap_vals = shap_values[1][0]
    elif len(shap_values.shape) == 2:
        shap_vals = shap_values[0]
    else:
        shap_vals = shap_values

    # ── 7. Fraud hard-override — fires regardless of model score ──────────
    if features.get('p2p_circular_loop_flag', 0) == 1:
        pd_score = max(pd_score, 0.85)
    if features.get('identity_device_mismatch', 0) == 1:
        pd_score = max(pd_score, 0.75)

    # ── 8. Grade + reason codes ───────────────────────────────────────────
    grade, outcome = _grade(pd_score)
    shap_reasons = _shap_reasons(shap_vals, list(feature_list))
    primary_reason = shap_reasons[0]['reason'] if shap_reasons else 'Model assessed profile'

    # ── 9. Normalized SHAP breakdown for frontend ─────────────────────────
    shap_dict = dict(zip(feature_list, shap_vals))
    max_abs = max((abs(v) for v in shap_dict.values()), default=1) or 1
    shap_normalized = {k: round(float(v) / max_abs, 4) for k, v in shap_dict.items()}

    return {
        'grade': grade,
        'outcome': outcome,
        'default_probability': round(pd_score, 4),
        'decision_source': 'model',
        'primary_reason': primary_reason,
        'shap_reasons': shap_reasons,
        'shap_breakdown': shap_normalized,
        'features': features,
        'loan_offer': _loan_offer(grade, features),
    }
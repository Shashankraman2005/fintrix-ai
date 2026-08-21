"""Middleman Feature Engine — master orchestrator.
Takes data from up to 5 middlemen, extracts features,
merges, reconciles conflicts, fills defaults.
Produces a complete feature dict compatible with the NTC model.
"""
import logging
import numpy as np

from middleman.extractors.supplier_extractor import extract as extract_supplier
from middleman.extractors.gst_extractor import extract as extract_gst
from middleman.extractors.telecom_extractor import extract as extract_telecom
from middleman.extractors.utility_extractor import extract as extract_utility
from middleman.extractors.bc_agent_extractor import extract as extract_bc_agent

logger = logging.getLogger("middleman_engine")

POPULATION_DEFAULTS = {
    "utility_payment_consistency": 0.75,
    "avg_utility_dpd": 8.0,
    "rent_wallet_share": 0.35,
    "subscription_commitment_ratio": 0.10,
    "emergency_buffer_months": 2.0,
    "eod_balance_volatility": 0.35,
    "essential_vs_lifestyle_ratio": 0.65,
    "cash_withdrawal_dependency": 0.40,
    "bounced_transaction_count": 1,
    "telecom_recharge_drop_ratio": 0.20,
    "min_balance_violation_count": 1,
    "vendor_payment_discipline": 0.70,
    "avg_invoice_payment_delay": 8.0,
    "business_vintage_months": 12.0,
    "cashflow_volatility": 0.40,
    "revenue_growth_trend": 0.0,
    "operating_cashflow_ratio": 0.75,
    "customer_concentration_ratio": 0.55,
    "repeat_customer_revenue_pct": 0.50,
    "gst_filing_consistency_score": 5.0,
    "gst_to_bank_variance": 0.30,
    "revenue_seasonality_index": 0.25,
    "telecom_number_vintage_days": 365,
    "identity_device_mismatch": 0,
    "turnover_inflation_spike": 0,
    "benford_anomaly_score": 0.20,
    "round_number_spike_ratio": 0.15,
    "p2p_circular_loop_flag": 0,
    # NEW UPI-calibrated features
    "night_transaction_ratio": 0.05,
    "weekend_spending_ratio": 0.28,
    "payment_diversity_score": 0.50,
    "device_consistency_score": 0.80,
    "geographic_risk_score": 2,
}

# Features that can come from multiple extractors — reconciliation rules
CONFLICT_RULES = {
    "business_vintage_months": "max",
    "bounced_transaction_count": "max",
    "eod_balance_volatility": "mean",
    "identity_device_mismatch": "max",
    "cash_withdrawal_dependency": "mean",
    "revenue_growth_trend": "mean",
}


class InsufficientDataError(Exception):
    pass


def extract_middleman_features(
    supplier_data: dict = None,
    gst_data: dict = None,
    telecom_data: dict = None,
    utility_data: dict = None,
    bc_agent_data: dict = None,
    applicant_metadata: dict = None,
) -> dict:
    # ── Step 1: Run available extractors ──────────────────────
    raw_results = []  # list of dicts from each extractor
    sources_available = 0

    if supplier_data:
        raw_results.append(extract_supplier(supplier_data))
        sources_available += 1

    if gst_data:
        raw_results.append(extract_gst(gst_data))
        sources_available += 1

    if telecom_data:
        raw_results.append(extract_telecom(telecom_data))
        sources_available += 1

    if utility_data:
        raw_results.append(extract_utility(utility_data))
        sources_available += 1

    if bc_agent_data:
        raw_results.append(extract_bc_agent(bc_agent_data))
        sources_available += 1

    # ── Step 2: Minimum viable data ──────────────────────────
    if sources_available < 2:
        raise InsufficientDataError(
            f"Minimum 2 middlemen required for scoring. "
            f"Only {sources_available} provided."
        )

    # ── Step 3: Confidence ───────────────────────────────────
    confidence_score = sources_available / 5
    if sources_available >= 4:
        confidence_level = "HIGH"
    elif sources_available >= 3:
        confidence_level = "MEDIUM"
    else:
        confidence_level = "LOW"

    # ── Step 4: Reconcile conflicting features ───────────────
    # Collect all values per feature across extractors
    all_values = {}
    for res in raw_results:
        for k, v in res.items():
            if k.startswith("data_source_"):
                continue
            if k not in all_values:
                all_values[k] = []
            all_values[k].append(v)

    results = {}
    for feat, values in all_values.items():
        if feat in CONFLICT_RULES and len(values) > 1:
            rule = CONFLICT_RULES[feat]
            if rule == "max":
                results[feat] = max(values)
            elif rule == "mean":
                results[feat] = round(sum(values) / len(values), 4)
        else:
            results[feat] = values[-1]  # latest extractor wins

    # ── Step 5: Apply population defaults for missing ────────
    for feat, default in POPULATION_DEFAULTS.items():
        if feat not in results:
            results[feat] = default

    # ── Step 6: Demographics from metadata ───────────────────
    metadata = applicant_metadata or {}

    results["applicant_age_years"] = float(
        metadata.get("applicant_age_years", 35))
    results["employment_vintage_days"] = float(
        results.get("business_vintage_months", 12) * 30)
    results["academic_background_tier"] = int(
        metadata.get("academic_background_tier", 2))
    results["owns_property"] = int(
        metadata.get("owns_property", 0))
    results["owns_car"] = int(
        metadata.get("owns_car", 0))
    results["region_risk_tier"] = int(
        metadata.get("region_risk_tier", 2))
    results["address_stability_years"] = float(
        metadata.get("address_stability_years", 3.0))
    results["id_document_age_years"] = float(
        metadata.get("id_document_age_years", 5.0))
    results["family_burden_ratio"] = float(
        metadata.get("family_burden_ratio", 0.2))
    results["income_type_risk_score"] = int(
        metadata.get("income_type_risk_score", 3))
    results["family_status_stability_score"] = int(
        metadata.get("family_status_stability_score", 2))
    results["contactability_score"] = int(
        metadata.get("contactability_score", 2))
    results["purpose_of_loan_encoded"] = int(
        metadata.get("purpose_of_loan_encoded", 1))
    results["car_age_years"] = int(
        metadata.get("car_age_years", 99))
    results["region_city_risk_score"] = int(
        metadata.get("region_city_risk_score", 2))
    results["address_work_mismatch"] = int(
        metadata.get("address_work_mismatch", 0))
    results["has_email_flag"] = int(
        metadata.get("has_email_flag", 0))
    results["telecom_number_vintage_days"] = int(
        results.get("telecom_number_vintage_days",
                     metadata.get("telecom_number_vintage_days", 365)))
    results["neighbourhood_default_rate_30"] = float(
        metadata.get("neighbourhood_default_rate_30", 0.07))
    results["neighbourhood_default_rate_60"] = float(
        metadata.get("neighbourhood_default_rate_60", 0.07))
    results["employment_to_age_ratio"] = float(min(1.0, max(0.0,
        results["employment_vintage_days"] /
        max(1, (results["applicant_age_years"] - 18) * 365)
    )))

    # Additional features the model may expect
    results.setdefault("income_stability_score", 0.5)
    results.setdefault("income_seasonality_flag", 0)
    # NEW UPI-calibrated features
    results.setdefault("night_transaction_ratio", 0.05)
    results.setdefault("weekend_spending_ratio", 0.28)
    results.setdefault("payment_diversity_score", 0.50)
    results.setdefault("device_consistency_score", 0.80)
    results.setdefault("geographic_risk_score", 2)

    # ── Step 7: Metadata ─────────────────────────────────────
    results["data_source"] = "middleman"
    results["sources_used"] = sources_available
    results["confidence_level"] = confidence_level
    results["confidence_score"] = confidence_score
    results["sources_available"] = {
        "supplier": supplier_data is not None,
        "gst": gst_data is not None,
        "telecom": telecom_data is not None,
        "utility": utility_data is not None,
        "bc_agent": bc_agent_data is not None,
    }

    # ── Step 8: Validate ─────────────────────────────────────
    # Check no None/NaN in numeric features
    for k, v in results.items():
        if isinstance(v, (dict, bool, str, list)):
            continue
        if v is None:
            raise ValueError(f"Feature {k} is None")
        if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
            raise ValueError(f"Feature {k} is NaN/Inf")

    logger.info(
        f"Middleman features extracted from {sources_available}/5 sources. "
        f"Confidence: {confidence_level}"
    )

    return results

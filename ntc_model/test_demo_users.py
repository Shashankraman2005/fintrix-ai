"""
Test v2 NTC model on demo_users.json.
Integrates pre_layer rules + ML model scoring.
Adapts demo_users.json transaction format to feature_engine format.
"""
import json
import sys
import os
import joblib
import numpy as np
import pandas as pd

# Ensure we import from THIS directory first (ntc_model)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from feature_engine import extract_features

# pre_layer is in parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pre_layer import apply_pre_layer


def classify_narration(narration: str) -> str:
    """Classify transaction narration into feature_engine categories."""
    n = narration.upper()
    if any(k in n for k in ["ELECTRICITY", "BILL PAYMENT", "BESCOM", "MSEDCL",
                             "BROADBAND", "FIBERNET", "GAS BILL", "WATER BILL"]):
        return "UTILITY"
    if any(k in n for k in ["RENT PAYMENT", "RENT OWNER"]):
        return "RENT"
    if any(k in n for k in ["ATM CASH", "CASH WITHDRAWAL"]):
        return "CASH_WITHDRAWAL"
    if "CHEQUE BOUNCE" in n or "CHQ BOUNCE" in n:
        return "BOUNCE"
    if "EMI" in n or "LOAN" in n:
        return "EMI"
    if any(k in n for k in ["GROCERY", "RESTAURANT", "DMART", "LULU",
                             "MEDICAL", "PHARMACY", "FUEL", "PETROL",
                             "TRANSPORT", "REPAIR", "MAINTENANCE",
                             "SEEDS", "FERTILIZER", "LABOUR", "WAGES",
                             "MACHINE", "TOOL", "FAMILY SUPPORT",
                             "DELIVERY", "PURCHASE", "RAW MATERIAL"]):
        return "LIFESTYLE"
    if any(k in n for k in ["UPI TRANSFER", "UPI CIRCULAR"]):
        return "UPI_TRANSFER"
    return "OTHER"


def compute_gst_to_bank_variance(user: dict, total_bank_credits: float) -> float:
    """Compute GST to bank variance from user data."""
    gst = user.get("gst_data", {})
    if not gst.get("available", False):
        return 0.0
    declared = gst.get("declared_turnover", 0)
    if total_bank_credits == 0 or declared == 0:
        return 0.0
    # Variance = abs difference / max
    return round(abs(declared - total_bank_credits) / max(declared, total_bank_credits), 4)


def adapt_demo_user(user: dict) -> dict:
    """Convert demo_users.json format to feature_engine expected format."""
    txns = user["transactions"]
    profile = user.get("user_profile", {})

    adapted_txns = []
    total_bank_credits = 0.0

    for t in txns:
        amount = abs(t["amount"])
        tx_type = "DR" if t["type"] == "DEBIT" else "CR"
        category = classify_narration(t.get("narration", ""))

        # Credits are INCOME (feature_engine expects "INCOME" not "SALARY")
        if tx_type == "CR":
            category = "INCOME"
            total_bank_credits += amount

        adapted_txns.append({
            "date": t["date"],
            "type": tx_type,
            "amount": amount,
            "description": t.get("narration", ""),
            "category": category,
            "balance": t["balance"],
            "txn_id": f"txn_{t['date']}_{amount}"
        })

    dates = [t["date"] for t in txns]
    biz_months = profile.get("business_vintage_months", 24)
    gst_variance = compute_gst_to_bank_variance(user, total_bank_credits)

    statement = {
        "user_id": user["user_id"],
        "statement_start": min(dates),
        "statement_end": max(dates),
        "transactions": adapted_txns,
        "applicant_metadata": {
            "applicant_age_years": 35,
            "employment_vintage_days": biz_months * 30,
            "income_type_risk_score": 1 if profile.get("academic_background_tier", 2) == 1 else 2,
            "owns_property": 0,
            "owns_car": 0,
            "region_risk_tier": 2,
            "region_city_risk_score": 2,
            "address_stability_years": biz_months / 12,
            "family_burden_ratio": 0.2,
            "family_status_stability_score": 2,
            "contactability_score": 2,
            "address_work_mismatch": 0,
            "academic_background_tier": profile.get("academic_background_tier", 2),
            "id_document_age_years": 5.0,
            "car_age_years": 99,
            "has_email_flag": 1,
            # Pre-layer metadata
            "gst_to_bank_variance": gst_variance,
            "gst_filing_consistency_score": profile.get("gst_filing_consistency_score", 0),
            "business_vintage_months": biz_months,
            "telecom_number_vintage_days": profile.get("telecom_number_vintage_days", 365),
            "turnover_inflation_spike": 0,
            "identity_device_mismatch": 0,
        }
    }
    return statement


def main():
    with open("../demo_users.json", encoding="utf-8") as f:
        data = json.load(f)

    users = data["demo_users"]
    print(f"Found {len(users)} demo users\n")

    model = joblib.load("models/ntc_credit_model.pkl")
    preprocessor = joblib.load("models/ntc_preprocessor.pkl")

    KEY_FEATURES = [
        "utility_payment_consistency", "eod_balance_volatility",
        "emergency_buffer_months", "bounced_transaction_count",
        "rent_wallet_share", "cash_withdrawal_dependency",
        "income_stability_score", "income_seasonality_flag",
        "p2p_circular_loop_flag", "customer_concentration_ratio",
        "revenue_seasonality_index", "revenue_growth_trend",
        "cashflow_volatility",
    ]

    correct = 0
    total = len(users)

    print("=" * 70)
    for user in users:
        uid = user["user_id"]
        persona = user["persona"]
        expected = user["expected_outcome"]

        statement = adapt_demo_user(user)
        features = extract_features(statement)

        # ─── PRE-LAYER CHECK ───
        pre_result = apply_pre_layer(features)

        if pre_result is not None:
            grade, decision, reason = pre_result
            source = "PRE-LAYER"
            p_default = 0.99 if decision == "REJECTED" else (0.45 if decision == "MANUAL REVIEW" else 0.10)
        else:
            # ─── ML MODEL ───
            source = "ML MODEL"
            df = pd.DataFrame([features])
            X = preprocessor.transform(df)
            p_default = model.predict_proba(X)[0][1]

            if p_default < 0.35:
                decision = "APPROVED"
            elif p_default < 0.55:
                decision = "MANUAL REVIEW"
            else:
                decision = "REJECTED"
            grade = "A" if decision == "APPROVED" else ("C" if decision == "MANUAL REVIEW" else "E")
            reason = "ML model prediction"

        # ─── MATCH CHECK ───
        exp_upper = expected.upper()
        dec_upper = decision.upper()
        match = (
            ("APPROV" in dec_upper and "APPROV" in exp_upper) or
            ("REJECT" in dec_upper and "REJECT" in exp_upper) or
            ("MANUAL" in dec_upper and ("MANUAL" in exp_upper or "CONDITION" in exp_upper))
        )
        if match:
            correct += 1

        print(f"User        : {uid} - {persona}")
        print(f"Source      : {source}")
        print(f"Grade       : {grade}")
        print(f"P(default)  : {p_default:.4f}")
        print(f"Decision    : {decision}")
        print(f"Expected    : {expected}")
        print(f"Match       : {'✓' if match else '✗'}")
        if pre_result:
            print(f"Rule reason : {reason}")
        print(f"Key features:")
        for kf in KEY_FEATURES:
            v = features.get(kf, "N/A")
            if isinstance(v, float):
                v = round(v, 4)
            print(f"  {kf:40s} {v}")
        print("=" * 70)

    print(f"\nProfiles correct: {correct} / {total}")


if __name__ == "__main__":
    main()

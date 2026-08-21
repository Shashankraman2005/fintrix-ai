"""End-to-end test for middleman data path.
Loads demo JSON, extracts features, scores with NTC model.
"""
import json, os, sys
import pandas as pd
import joblib
import warnings

warnings.filterwarnings("ignore")

# Ensure imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from middleman.middleman_feature_engine import (
    extract_middleman_features,
    InsufficientDataError,
)

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "demo_data", "middleman")
MODEL_DIR = os.path.join(os.path.dirname(BASE), "ntc_model", "models")
if not os.path.exists(MODEL_DIR):
    MODEL_DIR = os.path.join(BASE, "..", "models")


def load_json(profile, source):
    path = os.path.join(DATA_DIR, f"{profile}_{source}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


PROFILES = {
    "full_data_good_kirana": {
        "sources": ["supplier", "gst", "telecom", "utility", "bc_agent"],
        "expected": "APPROVE",
        "metadata": {
            "applicant_age_years": 45,
            "academic_background_tier": 3,
            "owns_property": 1,
            "owns_car": 0,
            "region_risk_tier": 2,
            "address_stability_years": 6.0,
            "id_document_age_years": 6.0,
            "family_burden_ratio": 0.20,
            "income_type_risk_score": 2,
            "family_status_stability_score": 1,
            "contactability_score": 3,
            "purpose_of_loan_encoded": 1,
            "car_age_years": 99,
            "region_city_risk_score": 2,
            "address_work_mismatch": 0,
            "has_email_flag": 0,
            "neighbourhood_default_rate_30": 0.05,
            "neighbourhood_default_rate_60": 0.05,
        },
    },
    "partial_data_growing_msme": {
        "sources": ["supplier", "gst", "telecom"],
        "expected": "MANUAL_REVIEW",
        "metadata": {
            "applicant_age_years": 32,
            "academic_background_tier": 3,
            "owns_property": 0,
            "owns_car": 0,
            "region_risk_tier": 2,
            "address_stability_years": 3.0,
            "id_document_age_years": 3.0,
            "family_burden_ratio": 0.30,
            "income_type_risk_score": 2,
            "family_status_stability_score": 2,
            "contactability_score": 2,
            "purpose_of_loan_encoded": 1,
            "car_age_years": 99,
            "region_city_risk_score": 2,
            "address_work_mismatch": 0,
            "has_email_flag": 1,
            "neighbourhood_default_rate_30": 0.06,
            "neighbourhood_default_rate_60": 0.06,
        },
    },
    "minimal_data_stressed": {
        "sources": ["utility", "bc_agent"],
        "expected": "REJECT",
        "metadata": {
            "applicant_age_years": 26,
            "academic_background_tier": 1,
            "owns_property": 0,
            "owns_car": 0,
            "region_risk_tier": 3,
            "address_stability_years": 1.0,
            "id_document_age_years": 1.0,
            "family_burden_ratio": 0.55,
            "income_type_risk_score": 4,
            "family_status_stability_score": 3,
            "contactability_score": 1,
            "purpose_of_loan_encoded": 1,
            "car_age_years": 99,
            "region_city_risk_score": 3,
            "address_work_mismatch": 1,
            "has_email_flag": 0,
            "neighbourhood_default_rate_30": 0.10,
            "neighbourhood_default_rate_60": 0.11,
        },
    },
    "new_business_clean": {
        "sources": ["supplier", "gst", "telecom"],
        "expected": "MANUAL_REVIEW",
        "metadata": {
            "applicant_age_years": 38,
            "academic_background_tier": 3,
            "owns_property": 0,
            "owns_car": 0,
            "region_risk_tier": 2,
            "address_stability_years": 4.0,
            "id_document_age_years": 4.0,
            "family_burden_ratio": 0.25,
            "income_type_risk_score": 2,
            "family_status_stability_score": 2,
            "contactability_score": 3,
            "purpose_of_loan_encoded": 1,
            "car_age_years": 99,
            "region_city_risk_score": 2,
            "address_work_mismatch": 0,
            "has_email_flag": 1,
            "neighbourhood_default_rate_30": 0.06,
            "neighbourhood_default_rate_60": 0.06,
        },
    },
}

KEY_FEATURES = [
    "vendor_payment_discipline",
    "gst_filing_consistency_score",
    "telecom_number_vintage_days",
    "utility_payment_consistency",
    "emergency_buffer_months",
    "bounced_transaction_count",
    "benford_anomaly_score",
    "business_vintage_months",
]


def run_test():
    # Load model
    model_path = os.path.join(BASE, "..", "models", "ntc_credit_model.pkl")
    preproc_path = os.path.join(BASE, "..", "models", "ntc_preprocessor.pkl")

    if not os.path.exists(model_path):
        print(f"[ERROR] Model not found: {model_path}")
        return
    if not os.path.exists(preproc_path):
        print(f"[ERROR] Preprocessor not found: {preproc_path}")
        return

    model = joblib.load(model_path)
    preprocessor = joblib.load(preproc_path)

    correct = 0
    conf_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for profile_name, config in PROFILES.items():
        # Load middleman data
        supplier = load_json(profile_name, "supplier") if "supplier" in config["sources"] else None
        gst = load_json(profile_name, "gst") if "gst" in config["sources"] else None
        telecom = load_json(profile_name, "telecom") if "telecom" in config["sources"] else None
        utility = load_json(profile_name, "utility") if "utility" in config["sources"] else None
        bc_agent = load_json(profile_name, "bc_agent") if "bc_agent" in config["sources"] else None

        features = extract_middleman_features(
            supplier_data=supplier,
            gst_data=gst,
            telecom_data=telecom,
            utility_data=utility,
            bc_agent_data=bc_agent,
            applicant_metadata=config["metadata"],
        )

        conf_level = features["confidence_level"]
        n_sources = features["sources_used"]
        conf_counts[conf_level] = conf_counts.get(conf_level, 0) + 1

        # Score with model
        feat_only = {k: v for k, v in features.items()
                     if not isinstance(v, (dict, bool, str, list))}
        df = pd.DataFrame([feat_only])
        try:
            X = preprocessor.transform(df)
            prob = float(model.predict_proba(X)[0][1])
        except Exception as e:
            print(f"[WARN] Preprocessor failed for {profile_name}, using raw: {e}")
            feat_names = model.get_booster().feature_names
            row = {f: feat_only.get(f, 0.0) for f in feat_names}
            df = pd.DataFrame([row])
            prob = float(model.predict_proba(df)[0][1])

        # Confidence-adjusted thresholds:
        # HIGH (5/5) → standard thresholds
        # MEDIUM (3-4) → tighter APPROVE bar (need stronger signal)
        # LOW (2) → even tighter (most data is defaulted)
        if conf_level == "HIGH":
            approve_thresh, review_thresh = 0.35, 0.55
        elif conf_level == "MEDIUM":
            approve_thresh, review_thresh = 0.20, 0.50
        else:  # LOW
            approve_thresh, review_thresh = 0.15, 0.45

        if prob < approve_thresh:
            decision = "APPROVE"
        elif prob < review_thresh:
            decision = "MANUAL_REVIEW"
        else:
            decision = "REJECT"

        expected = config["expected"]
        match = decision == expected
        if match:
            correct += 1

        # Print source status
        src_status = []
        for s in ["supplier", "gst", "telecom", "utility", "bc_agent"]:
            if s in config["sources"]:
                src_status.append(f"{s} ✓")
            else:
                src_status.append(f"{s} ✗")

        print("══════════════════════════════════════════════════════")
        print(f"Profile       : {profile_name}")
        print(f"Sources used  : {n_sources}/5 ({conf_level} confidence)")
        print(f"Sources       : {src_status[0]}  {src_status[1]}  {src_status[2]}")
        print(f"                {src_status[3]}  {src_status[4]}")
        print("──────────────────────────────────────────────────────")
        print("Key features extracted:")
        for f in KEY_FEATURES:
            val = features.get(f, "MISSING")
            if isinstance(val, float):
                val = f"{val:.4f}"
            print(f"  {f:<40} : {val}")
        print("──────────────────────────────────────────────────────")
        print(f"Credit risk   : P(default) = {prob:.4f}")
        print(f"Decision      : {decision}")
        print(f"Confidence    : {conf_level}")
        print(f"Expected      : {expected}")
        print(f"Match         : {'✓ PASS' if match else '✗ FAIL'}")
        print("══════════════════════════════════════════════════════\n")

    print(f"  Profiles correct       : {correct} / {len(PROFILES)}")
    print()
    print("  ── Confidence coverage ──")
    print(f"  HIGH (5/5 sources)     : {conf_counts.get('HIGH', 0)} profiles")
    print(f"  MEDIUM (3-4 sources)   : {conf_counts.get('MEDIUM', 0)} profiles")
    print(f"  LOW (2 sources)        : {conf_counts.get('LOW', 0)} profiles")
    print()

    # ── Insufficient data test ──
    try:
        extract_middleman_features(supplier_data={"invoices": []})
        print("  [FAIL] Insufficient data NOT rejected")
        insuf_ok = False
    except InsufficientDataError:
        print("  [OK] Insufficient data correctly rejected")
        insuf_ok = True

    print()
    print('  ── Demo message ──')
    print('  "These MSMEs have NO bank account, NO UPI history,')
    print('   NO AA data. Scored using middleman data only.')
    print('   Same model. Same pipeline. Same decision quality.')
    print('   30 million cash-only MSMEs can now access credit."')
    print()
    status = "READY" if correct >= 3 and insuf_ok else "NEEDS FIXING"
    print(f"  Demo pipeline status   : {status}")


if __name__ == "__main__":
    run_test()

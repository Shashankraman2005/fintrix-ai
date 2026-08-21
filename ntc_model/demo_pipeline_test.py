import pandas as pd
import numpy as np
import joblib
from feature_engine import extract_features
from synthetic_transaction_generator import generate_all_demo_profiles
import warnings

warnings.filterwarnings('ignore')

def run_demo():
    profiles = generate_all_demo_profiles(".")
    
    results = {}
    for profile_name, statement in profiles.items():
        features = extract_features(statement)
        results[profile_name] = features
        
    check_cols = [
        "utility_payment_consistency",
        "eod_balance_volatility",
        "rent_wallet_share",
        "emergency_buffer_months",
        "bounced_transaction_count",
        "employment_vintage_days",
        "cash_withdrawal_dependency"
    ]
    means = pd.Series({c: 0.5 for c in check_cols})
    stds = pd.Series({c: 0.1 for c in check_cols})
    
    misaligned_count = 0
    misaligned_details = []
    
    for profile_name, feats in results.items():
        for col in check_cols:
            tm = means[col]
            ts = stds[col]
            dv = feats[col]
            z = abs(dv - tm) / ts if ts > 0 else 0
            if z >= 2.0:
                misaligned_count += 1
                misaligned_details.append((col, z))
                
    model = joblib.load("models/ntc_credit_model.pkl")
    preprocessor = joblib.load("models/ntc_preprocessor.pkl")
    
    expected_map = {
        "good_salaried_ntc": "APPROVE",
        "stressed_gig_ntc": "MANUAL_REVIEW",
        "high_risk_ntc": "REJECT",
        "good_msme_owner": "APPROVE"
    }
    
    correct_count = 0
    failed_profiles = []
    
    failed_profiles = []
    
    KEY_FEATURES = [
        "utility_payment_consistency",
        "bounced_transaction_count",
        "eod_balance_volatility",
        "emergency_buffer_months",
        "rent_wallet_share",
        "employment_vintage_days",
        "applicant_age_years",
        "income_type_risk_score"
    ]
    
    for profile_name, features in results.items():
        print(f"\nKey features for {profile_name}:")
        for f in KEY_FEATURES:
            print(f"  {f:<40} {features.get(f, 'MISSING')}")
            
    profile_list = ["good_salaried_ntc", "stressed_gig_ntc", "high_risk_ntc", "good_msme_owner"]

    for profile_name in profile_list:
        if profile_name not in results:
            continue
        feats = results[profile_name]
        df = pd.DataFrame([feats])
        
        # The preprocessor pipeline might expect TARGET but transforming just uses valid predictors.
        # We ensure no ID or TARGET exists.
        X = preprocessor.transform(df)
        prob = model.predict_proba(X)[0][1]
        
        if prob < 0.35:
            decision = "APPROVE"
        elif prob < 0.55:
            decision = "MANUAL_REVIEW"
        else:
            decision = "REJECT"
            
        expected = expected_map.get(profile_name, "UNKNOWN")
        match_str = "✓ PASS" if decision == expected else "✗ FAIL"
        if decision == expected:
            correct_count += 1
        else:
            failed_profiles.append(profile_name)
            
        print("══════════════════════════════════════════════")
        print(f"Profile     : {profile_name}")
        print(f"P(default)  : {prob:.4f}")
        print(f"Decision    : {decision}")
        print(f"Expected    : {expected}")
        print(f"Match       : {match_str}")
        print("══════════════════════════════════════════════\n")
        
    print(f"Profiles correct    : {correct_count} / 4")
    print(f"Misaligned features : {misaligned_count}")
    
    if correct_count >= 3:
        status_msg = "Demo pipeline READY"
    else:
        status_msg = f"Demo pipeline NEEDS FIXING ({', '.join(failed_profiles)})"
        
    print(f"Demo pipeline status: {status_msg}\n")
    
    print("Top 3 misaligned features:")
    misaligned_details.sort(key=lambda x: x[1], reverse=True)
    seen = set()
    unique_misaligned = []
    for col, z in misaligned_details:
        if col not in seen:
            seen.add(col)
            unique_misaligned.append((col, z))
            
    for i, (col, z) in enumerate(unique_misaligned[:3], 1):
        print(f"{i}. {col} (z={z:.4f})")

if __name__ == "__main__":
    run_demo()

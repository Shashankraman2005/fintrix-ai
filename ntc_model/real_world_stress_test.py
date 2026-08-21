"""
Real-World Stress Test
======================
10 realistic Indian MSME/NTC profiles with KNOWN expected outcomes.
Tests whether the model gives intuitively correct rankings
even with circular training.

If a kirana store owner with 0 bounces and 8 years of utility payments
gets a HIGHER P(default) than a cash-only trader with 4 bounces,
the model is broken.
"""
import numpy as np
import pandas as pd
import joblib
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

model = joblib.load("models/ntc_credit_model.pkl")
preprocessor = joblib.load("models/ntc_preprocessor.pkl")

# The 32 features the model was trained on
FEATURE_COLS = [
    'utility_payment_consistency', 'avg_utility_dpd', 'rent_wallet_share',
    'subscription_commitment_ratio', 'emergency_buffer_months',
    'eod_balance_volatility', 'essential_vs_lifestyle_ratio',
    'cash_withdrawal_dependency', 'bounced_transaction_count',
    'telecom_number_vintage_days', 'academic_background_tier',
    'purpose_of_loan_encoded', 'employment_vintage_days',
    'telecom_recharge_drop_ratio', 'min_balance_violation_count',
    'applicant_age_years', 'owns_property', 'owns_car',
    'region_risk_tier', 'address_stability_years', 'id_document_age_years',
    'family_burden_ratio', 'has_email_flag', 'income_type_risk_score',
    'family_status_stability_score', 'contactability_score', 'car_age_years',
    'region_city_risk_score', 'address_work_mismatch',
    'employment_to_age_ratio',
    'neighbourhood_default_rate_30', 'neighbourhood_default_rate_60',
]

# ── 10 REALISTIC INDIAN PROFILES ──────────────────────────────
profiles = [
    {
        "name": "Rajesh - Kirana Store Owner, Pune (8 yrs)",
        "expected": "VERY LOW RISK",
        "features": {
            "utility_payment_consistency": 0.92,  # pays electricity every month
            "avg_utility_dpd": 2.0,               # barely late
            "rent_wallet_share": 0.15,             # owns shop, low rent
            "subscription_commitment_ratio": 0.03,
            "emergency_buffer_months": 4.5,        # good savings
            "eod_balance_volatility": 0.18,        # stable balance
            "essential_vs_lifestyle_ratio": 0.75,   # mostly essential spending
            "cash_withdrawal_dependency": 0.25,    # some cash (kirana normal)
            "bounced_transaction_count": 0,         # zero bounces
            "telecom_number_vintage_days": 2800,   # same number 7+ years
            "academic_background_tier": 2,          # 12th pass
            "purpose_of_loan_encoded": 1,
            "employment_vintage_days": 2920,       # 8 years
            "telecom_recharge_drop_ratio": 0.12,
            "min_balance_violation_count": 0,
            "applicant_age_years": 42,
            "owns_property": 1, "owns_car": 0,
            "region_risk_tier": 2, "address_stability_years": 10,
            "id_document_age_years": 12, "family_burden_ratio": 0.33,
            "has_email_flag": 0, "income_type_risk_score": 1,
            "family_status_stability_score": 1, "contactability_score": 2,
            "car_age_years": 99, "region_city_risk_score": 2,
            "address_work_mismatch": 0, "employment_to_age_ratio": 0.33,
            "neighbourhood_default_rate_30": 0.03,
            "neighbourhood_default_rate_60": 0.02,
        }
    },
    {
        "name": "Priya - Beautician, Bengaluru (3 yrs, growing)",
        "expected": "LOW RISK",
        "features": {
            "utility_payment_consistency": 0.83,
            "avg_utility_dpd": 5.0,
            "rent_wallet_share": 0.30,             # rents salon space
            "subscription_commitment_ratio": 0.05,
            "emergency_buffer_months": 2.5,
            "eod_balance_volatility": 0.28,
            "essential_vs_lifestyle_ratio": 0.65,
            "cash_withdrawal_dependency": 0.15,     # mostly digital payments
            "bounced_transaction_count": 0,
            "telecom_number_vintage_days": 1800,
            "academic_background_tier": 3,
            "purpose_of_loan_encoded": 1,
            "employment_vintage_days": 1095,
            "telecom_recharge_drop_ratio": 0.10,
            "min_balance_violation_count": 0,
            "applicant_age_years": 28,
            "owns_property": 0, "owns_car": 0,
            "region_risk_tier": 1, "address_stability_years": 3,
            "id_document_age_years": 5, "family_burden_ratio": 0.0,
            "has_email_flag": 1, "income_type_risk_score": 1,
            "family_status_stability_score": 4, "contactability_score": 3,
            "car_age_years": 99, "region_city_risk_score": 1,
            "address_work_mismatch": 0, "employment_to_age_ratio": 0.30,
            "neighbourhood_default_rate_30": 0.04,
            "neighbourhood_default_rate_60": 0.03,
        }
    },
    {
        "name": "Suresh - Auto Mechanic, Jaipur (marginal, cash heavy)",
        "expected": "MODERATE RISK",
        "features": {
            "utility_payment_consistency": 0.50,    # misses some months
            "avg_utility_dpd": 12.0,                # often late
            "rent_wallet_share": 0.40,              # high rent burden
            "subscription_commitment_ratio": 0.02,
            "emergency_buffer_months": 0.8,         # barely surviving
            "eod_balance_volatility": 0.55,         # unstable
            "essential_vs_lifestyle_ratio": 0.60,
            "cash_withdrawal_dependency": 0.60,     # mostly cash
            "bounced_transaction_count": 2,          # some bounces
            "telecom_number_vintage_days": 900,
            "academic_background_tier": 1,
            "purpose_of_loan_encoded": 1,
            "employment_vintage_days": 1825,
            "telecom_recharge_drop_ratio": 0.25,
            "min_balance_violation_count": 2,
            "applicant_age_years": 35,
            "owns_property": 0, "owns_car": 0,
            "region_risk_tier": 2, "address_stability_years": 4,
            "id_document_age_years": 8, "family_burden_ratio": 0.50,
            "has_email_flag": 0, "income_type_risk_score": 3,
            "family_status_stability_score": 1, "contactability_score": 1,
            "car_age_years": 99, "region_city_risk_score": 2,
            "address_work_mismatch": 0, "employment_to_age_ratio": 0.29,
            "neighbourhood_default_rate_30": 0.08,
            "neighbourhood_default_rate_60": 0.06,
        }
    },
    {
        "name": "Mohammed - Textile Trader, Surat (high volume, risky)",
        "expected": "HIGH RISK",
        "features": {
            "utility_payment_consistency": 0.40,
            "avg_utility_dpd": 18.0,
            "rent_wallet_share": 0.45,
            "subscription_commitment_ratio": 0.01,
            "emergency_buffer_months": 0.3,         # almost no buffer
            "eod_balance_volatility": 0.70,         # wild swings
            "essential_vs_lifestyle_ratio": 0.45,
            "cash_withdrawal_dependency": 0.55,
            "bounced_transaction_count": 4,          # multiple bounces
            "telecom_number_vintage_days": 400,      # new number
            "academic_background_tier": 2,
            "purpose_of_loan_encoded": 1,
            "employment_vintage_days": 730,
            "telecom_recharge_drop_ratio": 0.35,
            "min_balance_violation_count": 3,
            "applicant_age_years": 30,
            "owns_property": 0, "owns_car": 0,
            "region_risk_tier": 3, "address_stability_years": 1.5,
            "id_document_age_years": 4, "family_burden_ratio": 0.40,
            "has_email_flag": 0, "income_type_risk_score": 3,
            "family_status_stability_score": 2, "contactability_score": 1,
            "car_age_years": 99, "region_city_risk_score": 3,
            "address_work_mismatch": 1, "employment_to_age_ratio": 0.17,
            "neighbourhood_default_rate_30": 0.12,
            "neighbourhood_default_rate_60": 0.10,
        }
    },
    {
        "name": "Lakshmi - Tailoring Business, Chennai (steady, 5 yrs)",
        "expected": "VERY LOW RISK",
        "features": {
            "utility_payment_consistency": 0.88,
            "avg_utility_dpd": 3.0,
            "rent_wallet_share": 0.20,
            "subscription_commitment_ratio": 0.04,
            "emergency_buffer_months": 3.8,
            "eod_balance_volatility": 0.20,
            "essential_vs_lifestyle_ratio": 0.80,
            "cash_withdrawal_dependency": 0.20,
            "bounced_transaction_count": 0,
            "telecom_number_vintage_days": 2200,
            "academic_background_tier": 2,
            "purpose_of_loan_encoded": 1,
            "employment_vintage_days": 1825,
            "telecom_recharge_drop_ratio": 0.08,
            "min_balance_violation_count": 0,
            "applicant_age_years": 45,
            "owns_property": 1, "owns_car": 0,
            "region_risk_tier": 2, "address_stability_years": 12,
            "id_document_age_years": 15, "family_burden_ratio": 0.25,
            "has_email_flag": 0, "income_type_risk_score": 1,
            "family_status_stability_score": 1, "contactability_score": 2,
            "car_age_years": 99, "region_city_risk_score": 2,
            "address_work_mismatch": 0, "employment_to_age_ratio": 0.18,
            "neighbourhood_default_rate_30": 0.02,
            "neighbourhood_default_rate_60": 0.02,
        }
    },
    {
        "name": "Vikram - Food Cart, Delhi (new, unstable)",
        "expected": "HIGH RISK",
        "features": {
            "utility_payment_consistency": 0.33,
            "avg_utility_dpd": 20.0,
            "rent_wallet_share": 0.50,
            "subscription_commitment_ratio": 0.01,
            "emergency_buffer_months": 0.2,
            "eod_balance_volatility": 0.75,
            "essential_vs_lifestyle_ratio": 0.40,
            "cash_withdrawal_dependency": 0.70,     # mostly cash business
            "bounced_transaction_count": 3,
            "telecom_number_vintage_days": 300,
            "academic_background_tier": 1,
            "purpose_of_loan_encoded": 1,
            "employment_vintage_days": 365,
            "telecom_recharge_drop_ratio": 0.40,
            "min_balance_violation_count": 4,
            "applicant_age_years": 24,
            "owns_property": 0, "owns_car": 0,
            "region_risk_tier": 3, "address_stability_years": 1,
            "id_document_age_years": 2, "family_burden_ratio": 0.0,
            "has_email_flag": 0, "income_type_risk_score": 3,
            "family_status_stability_score": 4, "contactability_score": 1,
            "car_age_years": 99, "region_city_risk_score": 3,
            "address_work_mismatch": 1, "employment_to_age_ratio": 0.17,
            "neighbourhood_default_rate_30": 0.15,
            "neighbourhood_default_rate_60": 0.12,
        }
    },
    {
        "name": "Anita - Home Baker, Hyderabad (instagram business)",
        "expected": "LOW RISK",
        "features": {
            "utility_payment_consistency": 0.75,
            "avg_utility_dpd": 4.0,
            "rent_wallet_share": 0.10,              # works from home
            "subscription_commitment_ratio": 0.06,
            "emergency_buffer_months": 3.0,
            "eod_balance_volatility": 0.30,
            "essential_vs_lifestyle_ratio": 0.70,
            "cash_withdrawal_dependency": 0.08,     # fully digital (UPI)
            "bounced_transaction_count": 0,
            "telecom_number_vintage_days": 1500,
            "academic_background_tier": 4,
            "purpose_of_loan_encoded": 1,
            "employment_vintage_days": 730,
            "telecom_recharge_drop_ratio": 0.05,
            "min_balance_violation_count": 0,
            "applicant_age_years": 32,
            "owns_property": 1, "owns_car": 0,
            "region_risk_tier": 1, "address_stability_years": 6,
            "id_document_age_years": 8, "family_burden_ratio": 0.33,
            "has_email_flag": 1, "income_type_risk_score": 1,
            "family_status_stability_score": 1, "contactability_score": 4,
            "car_age_years": 99, "region_city_risk_score": 1,
            "address_work_mismatch": 0, "employment_to_age_ratio": 0.14,
            "neighbourhood_default_rate_30": 0.03,
            "neighbourhood_default_rate_60": 0.02,
        }
    },
    {
        "name": "Raju - Plumber, Lucknow (irregular income, honest)",
        "expected": "MODERATE RISK",
        "features": {
            "utility_payment_consistency": 0.58,
            "avg_utility_dpd": 10.0,
            "rent_wallet_share": 0.35,
            "subscription_commitment_ratio": 0.02,
            "emergency_buffer_months": 1.2,
            "eod_balance_volatility": 0.45,
            "essential_vs_lifestyle_ratio": 0.65,
            "cash_withdrawal_dependency": 0.45,
            "bounced_transaction_count": 1,
            "telecom_number_vintage_days": 2000,
            "academic_background_tier": 1,
            "purpose_of_loan_encoded": 1,
            "employment_vintage_days": 3650,
            "telecom_recharge_drop_ratio": 0.15,
            "min_balance_violation_count": 1,
            "applicant_age_years": 48,
            "owns_property": 0, "owns_car": 0,
            "region_risk_tier": 2, "address_stability_years": 8,
            "id_document_age_years": 10, "family_burden_ratio": 0.60,
            "has_email_flag": 0, "income_type_risk_score": 3,
            "family_status_stability_score": 1, "contactability_score": 1,
            "car_age_years": 99, "region_city_risk_score": 2,
            "address_work_mismatch": 0, "employment_to_age_ratio": 0.33,
            "neighbourhood_default_rate_30": 0.06,
            "neighbourhood_default_rate_60": 0.05,
        }
    },
    {
        "name": "Deepak - Cycle Repair, Village UP (very marginal)",
        "expected": "VERY HIGH RISK",
        "features": {
            "utility_payment_consistency": 0.25,     # rarely pays on time
            "avg_utility_dpd": 25.0,
            "rent_wallet_share": 0.55,
            "subscription_commitment_ratio": 0.0,
            "emergency_buffer_months": 0.1,          # almost nothing saved
            "eod_balance_volatility": 0.85,
            "essential_vs_lifestyle_ratio": 0.35,
            "cash_withdrawal_dependency": 0.80,      # all cash
            "bounced_transaction_count": 5,           # many bounces
            "telecom_number_vintage_days": 200,
            "academic_background_tier": 1,
            "purpose_of_loan_encoded": 1,
            "employment_vintage_days": 1460,
            "telecom_recharge_drop_ratio": 0.50,
            "min_balance_violation_count": 5,
            "applicant_age_years": 38,
            "owns_property": 0, "owns_car": 0,
            "region_risk_tier": 3, "address_stability_years": 2,
            "id_document_age_years": 5, "family_burden_ratio": 0.67,
            "has_email_flag": 0, "income_type_risk_score": 5,
            "family_status_stability_score": 1, "contactability_score": 0,
            "car_age_years": 99, "region_city_risk_score": 3,
            "address_work_mismatch": 0, "employment_to_age_ratio": 0.20,
            "neighbourhood_default_rate_30": 0.20,
            "neighbourhood_default_rate_60": 0.18,
        }
    },
    {
        "name": "Meena - Dairy Farm, Gujarat (seasonal but stable)",
        "expected": "LOW-MODERATE RISK",
        "features": {
            "utility_payment_consistency": 0.67,
            "avg_utility_dpd": 7.0,
            "rent_wallet_share": 0.05,               # owns land
            "subscription_commitment_ratio": 0.01,
            "emergency_buffer_months": 2.0,
            "eod_balance_volatility": 0.40,
            "essential_vs_lifestyle_ratio": 0.72,
            "cash_withdrawal_dependency": 0.35,
            "bounced_transaction_count": 1,
            "telecom_number_vintage_days": 1600,
            "academic_background_tier": 2,
            "purpose_of_loan_encoded": 1,
            "employment_vintage_days": 2555,
            "telecom_recharge_drop_ratio": 0.18,
            "min_balance_violation_count": 1,
            "applicant_age_years": 40,
            "owns_property": 1, "owns_car": 0,
            "region_risk_tier": 2, "address_stability_years": 15,
            "id_document_age_years": 12, "family_burden_ratio": 0.40,
            "has_email_flag": 0, "income_type_risk_score": 2,
            "family_status_stability_score": 1, "contactability_score": 2,
            "car_age_years": 99, "region_city_risk_score": 2,
            "address_work_mismatch": 0, "employment_to_age_ratio": 0.32,
            "neighbourhood_default_rate_30": 0.05,
            "neighbourhood_default_rate_60": 0.04,
        }
    },
]

# ── RUN TEST ──────────────────────────────────────────────────
print("=" * 72)
print("  REAL-WORLD STRESS TEST — 10 Realistic Indian MSME Profiles")
print("=" * 72)

results = []
for p in profiles:
    input_df = pd.DataFrame([p["features"]])[FEATURE_COLS]
    pd_score = float(model.predict_proba(input_df)[0][1])
    results.append((p["name"], p["expected"], pd_score))

# Sort by P(default) to check ranking
results_sorted = sorted(results, key=lambda x: x[2])

print(f"\n  {'Profile':<55} {'Expected':<20} {'P(def)':>8}  {'Grade'}")
print(f"  {'─'*55} {'─'*20} {'─'*8}  {'─'*5}")

for name, expected, pd_score in results_sorted:
    if pd_score < 0.05:    grade = "A"
    elif pd_score < 0.15:  grade = "B"
    elif pd_score < 0.35:  grade = "C"
    elif pd_score < 0.55:  grade = "D"
    else:                  grade = "E"
    print(f"  {name:<55} {expected:<20} {pd_score:>7.1%}  {grade}")

# ── RANKING CHECK ──────────────────────────────────────────────
print(f"\n{'─'*72}")
print("  RANKING SANITY CHECK")
print(f"{'─'*72}")

pd_dict = {r[0].split(" - ")[0]: r[2] for r in results}

checks = [
    ("Rajesh",  "<", "Suresh",   "Stable kirana < cash-heavy mechanic"),
    ("Rajesh",  "<", "Mohammed", "Stable kirana < risky textile trader"),
    ("Priya",   "<", "Mohammed", "Growing beautician < risky trader"),
    ("Lakshmi", "<", "Vikram",   "Steady tailor < unstable food cart"),
    ("Anita",   "<", "Deepak",   "Digital baker < marginal cycle repair"),
    ("Priya",   "<", "Suresh",   "Clean beautician < cash-heavy mechanic"),
    ("Meena",   "<", "Deepak",   "Stable dairy farm < marginal cycle repair"),
    ("Raju",    "<", "Deepak",   "Honest plumber < marginal cycle repair"),
]

passed = 0
failed = 0
for left_name, op, right_name, description in checks:
    left_pd = pd_dict[left_name]
    right_pd = pd_dict[right_name]
    
    if op == "<":
        ok = left_pd < right_pd
    
    status = "✅" if ok else "❌"
    if ok: passed += 1
    else:  failed += 1
    print(f"  {status} {description}")
    print(f"     {left_name} ({left_pd:.1%})  vs  {right_name} ({right_pd:.1%})")

print(f"\n  Ranking checks: {passed}/{passed+failed} correct")

if failed == 0:
    print("  ✅ MODEL RANKS ALL PROFILES IN CORRECT ORDER")
elif failed <= 2:
    print("  ⚠️  MOSTLY CORRECT — minor ranking issues")
else:
    print("  ❌ MODEL RANKING IS BROKEN")

print("=" * 72)

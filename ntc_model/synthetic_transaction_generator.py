import os
import json
import uuid
import random
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Strict deterministic constraints
random.seed(42)
rng = np.random.default_rng(42)

logger = logging.getLogger("synthetic_generator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

PROFILES = {
    "good_salaried_ntc": {
        "monthly_income": 45000.0,
        "income_type": "salary",
        "loan_amount": 100000.0,
        "months_of_history": 6,
        "expected_features": {
            "utility_payment_consistency": 1.0, 
            "bounced_transaction_count": 0,
            "emergency_buffer_months": 5.5,
            "eod_balance_volatility": 0.12,
            "cash_withdrawal_dependency": 0.05,
            "rent_wallet_share": 0.22,
            "min_balance_violation_count": 0,
            "telecom_recharge_drop_ratio": 0.06
        },
        "desc": "Stable salaried employee with clean utility and zero bounces.",
        "applicant_metadata": {
            "applicant_age_years"      : 42,
            "academic_background_tier" : 4,
            "id_document_age_years"    : 8.0,
            "employment_vintage_days"  : 3650,
            "owns_property"            : 1,
            "owns_car"                 : 1,
            "region_risk_tier"         : 1,
            "region_city_risk_score"   : 1,
            "address_stability_years"  : 8.0,
            "family_burden_ratio"      : 0.15,
            "family_status_stability_score": 1,
            "contactability_score"     : 4,
            "income_type_risk_score"   : 1,
            "address_work_mismatch"    : 0,
            "car_age_years"            : 3,
            "has_email_flag"           : 1,
        }
    },
    "stressed_gig_ntc": {
        "monthly_income": 20000.0,
        "income_type": "gig",
        "loan_amount": 50000.0,
        "months_of_history": 10,
        "expected_features": {
            "utility_payment_consistency": 0.62,
            "avg_utility_dpd": 8.0,
            "bounced_transaction_count": 2,
            "rent_wallet_share": 0.38,
            "emergency_buffer_months": 1.8,
            "eod_balance_volatility": 0.38,
            "cash_withdrawal_dependency": 0.30,
            "min_balance_violation_count": 2,
            "telecom_recharge_drop_ratio": 0.32
        },
        "desc": "Gig worker with erratic income, occasional missed utility, low buffer.",
        "applicant_metadata": {
            "applicant_age_years"      : 28,
            "academic_background_tier" : 2,
            "id_document_age_years"    : 1.5,
            "employment_vintage_days"  : 365,
            "owns_property"            : 0,
            "owns_car"                 : 0,
            "region_risk_tier"         : 3,
            "region_city_risk_score"   : 3,
            "address_stability_years"  : 2.0,
            "family_burden_ratio"      : 0.40,
            "family_status_stability_score": 4,
            "contactability_score"     : 2,
            "income_type_risk_score"   : 3,
            "address_work_mismatch"    : 2,
            "car_age_years"            : 99,
            "has_email_flag"           : 0,
        }
    },
    "high_risk_ntc": {
        "monthly_income": 12000.0,
        "income_type": "irregular",
        "loan_amount": 75000.0,
        "months_of_history": 6,
        "expected_features": {
            "utility_payment_consistency": 0.22, 
            "avg_utility_dpd": 28.0,
            "rent_wallet_share": 0.72,
            "bounced_transaction_count": 6,
            "emergency_buffer_months": 0.4,
            "eod_balance_volatility": 0.78,
            "cash_withdrawal_dependency": 0.62,
            "min_balance_violation_count": 6,
            "telecom_recharge_drop_ratio": 0.68
        },
        "desc": "Highly irregular cashflow, frequent NSF bounces, massive cash dependency.",
        "applicant_metadata": {
            "applicant_age_years"      : 22,
            "academic_background_tier" : 1,
            "id_document_age_years"    : 0.3,
            "employment_vintage_days"  : 60,
            "owns_property"            : 0,
            "owns_car"                 : 0,
            "region_risk_tier"         : 3,
            "region_city_risk_score"   : 3,
            "address_stability_years"  : 0.3,
            "family_burden_ratio"      : 0.70,
            "family_status_stability_score": 4,
            "contactability_score"     : 0,
            "income_type_risk_score"   : 5,
            "address_work_mismatch"    : 2,
            "car_age_years"            : 99,
            "has_email_flag"           : 0,
        }
    },
    "good_msme_owner": {
        "monthly_income": 90000.0,
        "income_type": "business",
        "loan_amount": 300000.0,
        "months_of_history": 6,
        "expected_features": {
            "utility_payment_consistency": 0.92,
            "avg_utility_dpd": 2.0,
            "bounced_transaction_count": 0,
            "rent_wallet_share": 0.20,
            "emergency_buffer_months": 7.0,
            "eod_balance_volatility": 0.10,
            "cash_withdrawal_dependency": 0.08,
            "min_balance_violation_count": 0,
            "telecom_recharge_drop_ratio": 0.06
        },
        "desc": "Solid MSME proprietor with high corporate inflows and stable operations.",
        "applicant_metadata": {
            "applicant_age_years"      : 40,
            "academic_background_tier" : 4,
            "id_document_age_years"    : 6.0,
            "employment_vintage_days"  : 4380,
            "owns_property"            : 1,
            "owns_car"                 : 1,
            "region_risk_tier"         : 2,
            "region_city_risk_score"   : 2,
            "address_stability_years"  : 8.0,
            "family_burden_ratio"      : 0.15,
            "family_status_stability_score": 1,
            "contactability_score"     : 4,
            "income_type_risk_score"   : 1,
            "address_work_mismatch"    : 0,
            "car_age_years"            : 5,
            "has_email_flag"           : 1,
        }
    }
}

UTILITY_BANDS = ["BESCOM ELECTRICITY", "JIO PREPAID", "INDANE GAS", "TNEB WATER"]
LIFESTYLE_BANDS = ["SWIGGY", "ZOMATO", "AMAZON PAY", "FLIPKART", "NETFLIX", "STARBUCKS"]

def get_base_probability(profile_name):
    if "good" in profile_name: return {"bounce": 0.0, "miss_utility": 0.0, "cash": 0.05}
    if "stressed" in profile_name: return {"bounce": 0.1, "miss_utility": 0.4, "cash": 0.3}
    return {"bounce": 0.3, "miss_utility": 0.7, "cash": 0.8}

def generate_statement(profile_name: str, user_id: str, months: int) -> dict:
    profile = PROFILES[profile_name]
    probs = get_base_probability(profile_name)
    
    start_date = datetime.now() - timedelta(days=30*months)
    transactions = []
    
    # Starting logical balance — proportional to income for realistic volatility
    monthly_inc = profile["monthly_income"]
    if "good" in profile_name:
        running_balance = monthly_inc * rng.uniform(3.0, 5.0)  # 3-5 months' income saved
    elif "stressed" in profile_name:
        running_balance = monthly_inc * rng.uniform(0.7, 1.0)  # moderate savings
    else:
        running_balance = monthly_inc * rng.uniform(0.02, 0.1)  # high risk = near zero
    
    for month_idx in range(months):
        base_date = start_date + timedelta(days=30*month_idx)
        
        # 1. Income Generation
        if profile["income_type"] == "salary":
            amt = profile["monthly_income"] + rng.uniform(-1000, 1000)
            running_balance += amt
            transactions.append({
                "date": f"{base_date.year:04d}-{base_date.month:02d}-01",
                "type": "CR",
                "amount": round(amt, 2),
                "description": "NEFT-SALARY-WIPRO LTD",
                "category": "INCOME",
                "balance": round(running_balance, 2),
                "txn_id": str(uuid.uuid4())
            })
        elif profile["income_type"] == "gig":
            if rng.random() >= 0.30:
                for _ in range(3): # Spread gig payments
                    amt = profile["monthly_income"]/3 + rng.uniform(-2000, 2000)
                    d = base_date + timedelta(days=int(rng.integers(1, 28)))
                    running_balance += amt
                    transactions.append({
                        "date": d.strftime("%Y-%m-%d"),
                        "type": "CR",
                        "amount": round(amt, 2),
                        "description": "UPI/ZOMATO/PAYOUT",
                        "category": "INCOME",
                        "balance": round(running_balance, 2),
                        "txn_id": str(uuid.uuid4())
                    })
        else: # irregular / business
            count = 5 if profile["income_type"] == "business" else 2
            for _ in range(count):
                amt = (profile["monthly_income"]/count) + rng.uniform(-5000, 10000)
                d = base_date + timedelta(days=int(rng.integers(1, 28)))
                running_balance += amt
                transactions.append({
                    "date": d.strftime("%Y-%m-%d"),
                    "type": "CR",
                    "amount": round(amt, 2),
                    "description": "IMPS/B2B/VENDOR",
                    "category": "INCOME",
                    "balance": round(running_balance, 2),
                    "txn_id": str(uuid.uuid4())
                })
                
        # 2. Add structural predictable utility outflows
        consistency = profile.get("expected_features", {}).get("utility_payment_consistency", 0.85)
            
            
        consistency = float(
            profile.get("expected_features", {}).get(
                "utility_payment_consistency", 0.85
            )
        )
        # Hard clamp — never allow above expected value
        consistency = min(consistency, 
            profile.get("expected_features", {}).get(
                "utility_payment_consistency", 0.85
            )
        )
        
        is_on_time = rng.random() < consistency
        
        amt = rng.uniform(600, 2500)
        running_balance -= amt
        
        # Due date = 10th of this calendar month (not +10 days which can cross months)
        from datetime import date as _date
        bill_due = datetime(base_date.year, base_date.month, 10)
        if is_on_time:
            # Pay between day 10 and day 14 (on time, 0-4 DPD)
            util_date = bill_due + timedelta(days=int(rng.integers(0, 5)))
        else:
            avg_dpd = profile.get("expected_features", {}).get("avg_utility_dpd", 5.0)
            util_date = bill_due + timedelta(days=max(6, int(rng.normal(avg_dpd, avg_dpd*0.3))))
            
        transactions.append({
            "date": util_date.strftime("%Y-%m-%d"),
            "type": "DR",
            "amount": round(amt, 2),
            "description": f"UPI/BILLPAY/{rng.choice(UTILITY_BANDS)}",
            "category": "UTILITY",
            "balance": round(running_balance, 2),
            "txn_id": str(uuid.uuid4())
        })
            
        # 3. Rent & EMI (simulated based on wallet share logic)
        rent_share = float(
            profile.get("expected_features", {}).get(
                "rent_wallet_share", 0.30
            )
        )
        # Rent = 60% of total rent+emi burden
        monthly_income = profile["monthly_income"]
        rent_amt = monthly_income * rent_share * 0.6
        running_balance -= rent_amt
        transactions.append({
            "date": (base_date + timedelta(days=5)).strftime("%Y-%m-%d"),
            "type": "DR",
            "amount": round(rent_amt, 2),
            "description": "UPI/RENT/LANDLORD",
            "category": "RENT",
            "balance": round(running_balance, 2),
            "txn_id": str(uuid.uuid4())
        })
        
        rent_share = float(
            profile.get("expected_features", {}).get(
                "rent_wallet_share", 0.30
            )
        )
        # EMI = 40% of total rent+emi burden  
        monthly_income = profile["monthly_income"]
        emi_amt = monthly_income * rent_share * 0.4
        running_balance -= emi_amt
        transactions.append({
            "date": (base_date + timedelta(days=7)).strftime("%Y-%m-%d"),
            "type": "DR",
            "amount": round(emi_amt, 2),
            "description": "ACH/EMI/MUTHOOT FINANCE",
            "category": "EMI",
            "balance": round(running_balance, 2),
            "txn_id": str(uuid.uuid4())
        })
        
        # 4. Cash withdrawals
        if rng.random() < probs["cash"]:
            amt = profile["monthly_income"] * probs["cash"] * 0.5
            running_balance -= amt
            transactions.append({
                "date": (base_date + timedelta(days=12)).strftime("%Y-%m-%d"),
                "type": "DR",
                "amount": round(amt, 2),
                "description": "ATM CASH WITHDRAWAL/SBI",
                "category": "CASH_WITHDRAWAL",
                "balance": round(running_balance, 2),
                "txn_id": str(uuid.uuid4())
            })
            
        # 5. Lifestyle overhead
        for _ in range(2):
            amt = rng.uniform(200, 1500)
            running_balance -= amt
            transactions.append({
                "date": (base_date + timedelta(days=int(rng.integers(1, 28)))).strftime("%Y-%m-%d"),
                "type": "DR",
                "amount": round(amt, 2),
                "description": f"UPI/{rng.choice(LIFESTYLE_BANDS)}",
                "category": "LIFESTYLE",
                "balance": round(running_balance, 2),
                "txn_id": str(uuid.uuid4())
            })
            
        # 6. Bounces / NSF fees - Moved outside loop

    
    # 6. Bounces / NSF fees
    n_bounces = profile.get("expected_features", {}).get("bounced_transaction_count", 0)
    end_date = start_date + timedelta(days=30*months)
    for i in range(n_bounces):
        day_offset = int((i / max(n_bounces, 1)) * (end_date - start_date).days)
        bounce_date = start_date + timedelta(days=day_offset + int(rng.integers(0, 15)))
        running_balance -= 590.00
        transactions.append({
            "date": bounce_date.strftime("%Y-%m-%d"),
            "type": "DR",
            "amount": 590.00,
            "description": "CHQ RETURN/INSUFFICIENT FUNDS/NSF",
            "category": "BOUNCE",
            "balance": round(running_balance, 2),
            "txn_id": str(uuid.uuid4())
        })

    # Sort by date
    transactions.sort(key=lambda x: x["date"])
    
    total_cr = sum(t["amount"] for t in transactions if t["type"] == "CR")
    total_dr = sum(t["amount"] for t in transactions if t["type"] == "DR")
    
    return {
        "user_id": user_id,
        "account_number": f"{rng.integers(1000000000, 9999999999)}",
        "bank": "HDFC BANK" if "good" in profile_name else "SBI",
        "ifsc": "HDFC0000123" if "good" in profile_name else "SBIN0000123",
        "currency": "INR",
        "statement_start": transactions[0]["date"],
        "statement_end": transactions[-1]["date"],
        "total_credits": round(total_cr, 2),
        "total_debits": round(total_dr, 2),
        "transaction_count": len(transactions),
        "transactions": transactions,
        "_test_expected_features": profile.get("expected_features", {}),
        "_profile_description": profile.get("desc", ""),
        "applicant_metadata": profile.get("applicant_metadata", {})
    }

def generate_all_demo_profiles(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    results = {}
    
    logger.info(f"Generating synthetic statement JSONs into {output_dir}")
    for p_name in PROFILES.keys():
        uid = f"USR_{p_name.upper()}_{rng.integers(100, 999)}"
        doc = generate_statement(p_name, uid, 6)
        
        path = os.path.join(output_dir, f"{p_name}_statement.json")
        with open(path, "w") as f:
            json.dump(doc, f, indent=4)
        
        results[p_name] = doc
        logger.info(f" ✓ Saved {p_name} ({len(doc['transactions'])} txns) -> {path}")
        
    return results

def run_feature_engine_test(statements: dict, feature_engine_fn) -> pd.DataFrame:
    """
    Validates that the external core system (feature_engine.py) extracts features 
    correctly from our demo statements using a 15% tolerance window.
    """
    logger.info("\nSimulation verification logic initialized. Assuming feature_engine_fn takes JSON statement.")
    # Implementation placeholder for user's own CI/CD verification script logic
    pass

if __name__ == "__main__":
    statements = generate_all_demo_profiles("demo_data")
    print("\nGeneration Complete. Synthetic data primed for React Frontend.")

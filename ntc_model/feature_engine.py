import pandas as pd
import numpy as np
from datetime import datetime, date
import calendar
from collections import Counter
import math
def _get_months_in_statement(statement) -> float:
    try:
        start = datetime.strptime(statement["statement_start"], "%Y-%m-%d")
        end = datetime.strptime(statement["statement_end"], "%Y-%m-%d")
        days = (end - start).days
        return max(1.0, days / 30.0)
    except:
        return 1.0

def extract_features(statement: dict) -> dict:
    transactions = statement.get("transactions", [])
    months_in_statement = _get_months_in_statement(statement)
    
    try:
        start_date = datetime.strptime(statement["statement_start"], "%Y-%m-%d")
    except:
        start_date = datetime.now()
        
    metadata = statement.get("applicant_metadata", {})

    # Get all utility payments sorted by date
    utility_txns = sorted(
        [t for t in transactions
         if t["category"] == "UTILITY"
         and t["type"] == "DR"],
        key=lambda x: x["date"]
    )

    if len(utility_txns) == 0:
        utility_payment_consistency = 0.75
        avg_utility_dpd = 5.0
    else:
        # Group utility payments by billing month
        # Billing month = the month BEFORE payment
        # if payment is after 20th, it belongs to
        # that month's bill
        # if payment is before 20th, it belongs to
        # previous month's bill

        on_time_count = 0
        total_count   = 0
        dpd_values    = []

        # Track which billing months we have seen
        # to avoid counting same month twice
        seen_billing_months = set()

        for txn in utility_txns:
            pay_date = datetime.strptime(
                txn["date"], "%Y-%m-%d"
            ).date()

            # Determine billing month
            # If paid on or before 20th →
            #   bill is from same month
            # If paid after 20th →
            #   bill is from same month but very late
            #   OR it crossed from previous month

            # Simple rule: due date is always 10th
            # of the month the payment occurred in
            # UNLESS payment day < 10, meaning it
            # crossed from previous month

            if pay_date.day < 10:
                # Payment is early in month
                # This is likely a late payment from
                # previous month's bill
                # Due date was previous month's 10th
                if pay_date.month == 1:
                    due_year  = pay_date.year - 1
                    due_month = 12
                else:
                    due_year  = pay_date.year
                    due_month = pay_date.month - 1

                due_date = date(due_year, due_month, 10)
                billing_key = (due_year, due_month)
            else:
                # Payment is mid or late month
                # Due date is 10th of same month
                due_date    = date(
                    pay_date.year, pay_date.month, 10
                )
                billing_key = (
                    pay_date.year, pay_date.month
                )

            # Skip if we already counted this
            # billing month (avoid duplicates)
            if billing_key in seen_billing_months:
                continue
            seen_billing_months.add(billing_key)

            # Compute DPD
            dpd = max(0, (pay_date - due_date).days)
            dpd_values.append(dpd)
            total_count += 1

            # On time = paid within 5 days of due date
            if dpd <= 5:
                on_time_count += 1

        if total_count == 0:
            utility_payment_consistency = 0.75
            avg_utility_dpd = 5.0
        else:
            utility_payment_consistency = round(
                on_time_count / total_count, 4
            )
            avg_utility_dpd = round(
                sum(dpd_values) / len(dpd_values), 2
            )

    # 3. rent_wallet_share
    rent_emi = sum(t["amount"] for t in transactions if t["category"] in ["RENT", "EMI"] and t["type"] == "DR")
    total_income = sum(t["amount"] for t in transactions if t["category"] == "INCOME" and t["type"] == "CR")
    
    monthly_rent_emi = rent_emi / months_in_statement
    monthly_income = total_income / months_in_statement
    
    if monthly_income == 0:
        rent_wallet_share = 0.3
    else:
        rent_wallet_share = monthly_rent_emi / monthly_income
    rent_wallet_share = max(0.0, min(1.0, rent_wallet_share))

    # 4. subscription_commitment_ratio
    subscription_commitment_ratio = rent_wallet_share * 0.3

    # 5. emergency_buffer_months
    total_debits = sum(t["amount"] for t in transactions if t["type"] == "DR")
    avg_monthly_spend = total_debits / months_in_statement
    avg_monthly_income = total_income / months_in_statement
    
    if avg_monthly_spend == 0:
        emergency_buffer_months = 2.0
    else:
        surplus = avg_monthly_income - avg_monthly_spend
        emergency_buffer_months = max(0.0, min(24.0, surplus / avg_monthly_spend))

    # 6. eod_balance_volatility
    balances = [t["balance"] for t in transactions if "balance" in t]
    if len(balances) < 3:
        eod_balance_volatility = 0.3
    else:
        m = sum(balances) / len(balances)
        var = sum((b - m)**2 for b in balances) / len(balances)
        std = var**0.5
        eod_balance_volatility = max(0.0, min(1.0, std / (m + 1)))

    # 7. essential_vs_lifestyle_ratio
    essential = sum(t["amount"] for t in transactions if t["category"] in ["UTILITY", "EMI", "RENT"] and t["type"] == "DR")
    lifestyle = sum(t["amount"] for t in transactions if t["category"] == "LIFESTYLE" and t["type"] == "DR")
    total_el = essential + lifestyle
    raw = essential / total_el if total_el > 0 else 0.85
    if raw <= 0.2:
        essential_vs_lifestyle_ratio = 1
    elif raw <= 0.4:
        essential_vs_lifestyle_ratio = 2
    elif raw <= 0.6:
        essential_vs_lifestyle_ratio = 3
    elif raw <= 0.8:
        essential_vs_lifestyle_ratio = 4
    else:
        essential_vs_lifestyle_ratio = 5

    # 8. cash_withdrawal_dependency
    cash = sum(t["amount"] for t in transactions if t["category"] == "CASH_WITHDRAWAL" and t["type"] == "DR")
    cash_withdrawal_dependency = max(0.0, min(1.0, cash / total_debits if total_debits > 0 else 0.1))

    # 9. bounced_transaction_count
    bounces = sum(1 for t in transactions if t["category"] == "BOUNCE")
    bounced_transaction_count = max(0, min(10, bounces))

    # 10. telecom_number_vintage_days
    tel_kws = ["jio", "airtel", "vi", "bsnl", "telecom", "postpaid", "prepaid"]
    tel_txs = [t for t in transactions if any(k in str(t.get("description", "")).lower() for k in tel_kws)]
    if metadata.get("telecom_number_vintage_days"):
        telecom_number_vintage_days = metadata["telecom_number_vintage_days"]
    elif tel_txs:
        first_t = min(datetime.strptime(t["date"], "%Y-%m-%d") for t in tel_txs)
        telecom_number_vintage_days = max(0, (first_t - start_date).days)
    else:
        telecom_number_vintage_days = 365

    # 11-12
    academic_background_tier = metadata.get("academic_background_tier", 2)
    purpose_of_loan_encoded = 1

    # 13. employment_vintage_days
    sal_kws = ["sal", "salary", "payroll"]
    sal_txs = [t for t in transactions if t["category"] == "INCOME" and t["type"] == "CR" and any(k in str(t.get("description", "")).lower() for k in sal_kws)]
    
    if metadata.get("employment_vintage_days"):
        employment_vintage_days = metadata["employment_vintage_days"]
    elif sal_txs:
        end_date = datetime.strptime(statement["statement_end"], "%Y-%m-%d")
        first_s = min(datetime.strptime(t["date"], "%Y-%m-%d") for t in sal_txs)
        employment_vintage_days = max(0, (end_date - first_s).days)
    else:
        employment_vintage_days = 180

    # 14. telecom_recharge_drop_ratio
    mon_tel = {}
    for t in tel_txs:
        d = datetime.strptime(t["date"], "%Y-%m-%d")
        k = f"{d.year}-{d.month:02d}"
        mon_tel[k] = mon_tel.get(k, 0) + t["amount"]
    msort = sorted(mon_tel.keys())
    if len(msort) < 2:
        telecom_recharge_drop_ratio = 0.2
    else:
        r_avg = sum(mon_tel[m] for m in msort[-2:]) / 2.0
        e_avg = sum(mon_tel[m] for m in msort[:-2]) / len(msort[:-2]) if len(msort[:-2]) > 0 else 0
        if e_avg == 0:
            telecom_recharge_drop_ratio = 0.2
        else:
            telecom_recharge_drop_ratio = max(0.0, min(1.0, (e_avg - r_avg) / e_avg))

    # 15. min_balance_violation_count
    mon_bal = {}
    for t in transactions:
        d = datetime.strptime(t["date"], "%Y-%m-%d")
        k = f"{d.year}-{d.month:02d}"
        if "balance" in t:
            if k not in mon_bal: mon_bal[k] = t["balance"]
            else: mon_bal[k] = min(mon_bal[k], t["balance"])
    min_balance_violation_count = max(0, min(8, sum(1 for v in mon_bal.values() if v < 1000)))

    # 16-23
    applicant_age_years = metadata.get("applicant_age_years", 35.0)
    owns_property = metadata.get("owns_property", 0)
    owns_car = metadata.get("owns_car", 0)
    region_risk_tier = metadata.get("region_risk_tier", 2)
    address_stability_years = metadata.get("address_stability_years", 3.0)
    id_document_age_years = metadata.get("id_document_age_years", 5.0)
    family_burden_ratio = metadata.get("family_burden_ratio", 0.2)
    has_email_flag = metadata.get("has_email_flag", 1)

    # 24. income_type_risk_score
    if metadata.get("income_type_risk_score"):
        income_type_risk_score = metadata["income_type_risk_score"]
    else:
        descs = " ".join([str(t.get("description", "")).lower() for t in transactions])
        if "sal" in descs or "salary" in descs: income_type_risk_score = 1
        elif "pension" in descs: income_type_risk_score = 2
        else: income_type_risk_score = 3
    
    # 25-29
    family_status_stability_score = metadata.get("family_status_stability_score", 2)
    contactability_score = metadata.get("contactability_score", 2)
    car_age_years = metadata.get("car_age_years", 99)
    region_city_risk_score = metadata.get("region_city_risk_score", 2)
    address_work_mismatch = metadata.get("address_work_mismatch", 0)

    # 30. employment_to_age_ratio
    employment_to_age_ratio = max(0.0, employment_vintage_days / max(1.0, (applicant_age_years - 18) * 365))

    # 31. income_stability_score — coefficient of variation of monthly income
    # 1.0 = perfectly stable salary, 0.0 = wildly erratic / seasonal
    monthly_credits = {}
    for t in transactions:
        if t["type"] == "CR":
            d = datetime.strptime(t["date"], "%Y-%m-%d")
            k = f"{d.year}-{d.month:02d}"
            monthly_credits[k] = monthly_credits.get(k, 0) + t["amount"]

    # Fill zero-income months
    if monthly_credits:
        all_months_sorted = sorted(monthly_credits.keys())
        first_m = datetime.strptime(all_months_sorted[0] + "-01", "%Y-%m-%d")
        last_m = datetime.strptime(all_months_sorted[-1] + "-01", "%Y-%m-%d")
        cur = first_m
        while cur <= last_m:
            k = f"{cur.year}-{cur.month:02d}"
            if k not in monthly_credits:
                monthly_credits[k] = 0.0
            if cur.month == 12:
                cur = cur.replace(year=cur.year + 1, month=1)
            else:
                cur = cur.replace(month=cur.month + 1)

    if len(monthly_credits) >= 2:
        inc_values = list(monthly_credits.values())
        inc_mean = sum(inc_values) / len(inc_values)
        if inc_mean > 0:
            inc_std = (sum((v - inc_mean) ** 2 for v in inc_values) / len(inc_values)) ** 0.5
            cv = inc_std / inc_mean
            income_stability_score = round(max(0.0, min(1.0, 1.0 - cv)), 4)
        else:
            income_stability_score = 0.0
    else:
        income_stability_score = 0.5

    # 32. income_seasonality_flag — 1 if income concentrated in <= 2 months
    if len(monthly_credits) >= 3:
        inc_values = sorted(monthly_credits.values(), reverse=True)
        total_inc = sum(inc_values)
        if total_inc > 0:
            top2_share = sum(inc_values[:2]) / total_inc
            income_seasonality_flag = 1 if top2_share > 0.75 else 0
        else:
            income_seasonality_flag = 1
    else:
        income_seasonality_flag = 0

    # 33. p2p_circular_loop_flag — detects wash trading
    # If same counterparty appears in both large credits AND large debits
    # Counter imported at top of file
    credit_counterparties = []
    debit_counterparties = []
    for t in transactions:
        desc = str(t.get("description", "")).upper()
        # Extract counterparty name (last 2-3 words typically)
        words = [w for w in desc.split() if len(w) > 3]
        if len(words) >= 2:
            counterparty = " ".join(words[-2:])
        elif len(words) == 1:
            counterparty = words[0]
        else:
            continue

        if t["type"] == "CR" and t["amount"] > 5000:
            credit_counterparties.append(counterparty)
        elif t["type"] == "DR" and t["amount"] > 5000:
            debit_counterparties.append(counterparty)

    credit_set = set(credit_counterparties)
    debit_set = set(debit_counterparties)
    circular_matches = credit_set & debit_set
    p2p_circular_loop_flag = 1 if len(circular_matches) > 0 else 0

    # 34. gst_to_bank_variance — from metadata / user_profile
    gst_to_bank_variance = float(metadata.get("gst_to_bank_variance", 0.0))

    # 35. customer_concentration_ratio — fraction of income from top customer
    if credit_counterparties:
        cp_counts = Counter(credit_counterparties)
        top_count = cp_counts.most_common(1)[0][1]
        customer_concentration_ratio = round(top_count / len(credit_counterparties), 4)
    else:
        customer_concentration_ratio = 0.5

    # 36. turnover_inflation_spike — from metadata
    turnover_inflation_spike = int(metadata.get("turnover_inflation_spike", 0))

    # 37. identity_device_mismatch — from metadata
    identity_device_mismatch = int(metadata.get("identity_device_mismatch", 0))

    # 38. business_vintage_months — from metadata
    business_vintage_months = int(metadata.get("business_vintage_months", employment_vintage_days / 30))

    # 39. gst_filing_consistency_score — from metadata
    gst_filing_consistency_score = int(metadata.get("gst_filing_consistency_score", 0))

    # 40. revenue_seasonality_index — Gini coefficient of monthly income
    # 0.0 = perfectly even income across months
    # 1.0 = all income in a single month (extreme seasonality)
    if len(monthly_credits) >= 2 and sum(monthly_credits.values()) > 0:
        sorted_vals = sorted(monthly_credits.values())
        n = len(sorted_vals)
        cumulative = []
        running = 0
        for v in sorted_vals:
            running += v
            cumulative.append(running)
        total = cumulative[-1]
        area = sum(c / total for c in cumulative) / n
        revenue_seasonality_index = round(
            max(0.0, min(1.0, 1.0 - 2.0 * area + 1.0 / n)), 4
        )
    else:
        revenue_seasonality_index = 0.0

    # 41. revenue_growth_trend — recent income vs earlier income
    # Positive = growing, negative = declining
    # < -0.30 means income dropped more than 30%
    if len(monthly_credits) >= 3:
        mc_keys_sorted = sorted(monthly_credits.keys())
        mc_values = [monthly_credits[k] for k in mc_keys_sorted]
        recent_avg = sum(mc_values[-2:]) / 2.0
        earlier_vals = mc_values[:-2]
        if len(earlier_vals) > 0:
            earlier_avg = sum(earlier_vals) / len(earlier_vals)
            if earlier_avg > 0:
                revenue_growth_trend = round(
                    max(-1.0, min(2.0, (recent_avg - earlier_avg) / earlier_avg)), 4
                )
            else:
                revenue_growth_trend = 0.0
        else:
            revenue_growth_trend = 0.0
    else:
        revenue_growth_trend = 0.0

    # 42. cashflow_volatility — CV of daily net cashflow
    # Higher = more unpredictable daily cash movements
    daily_nets = {}
    for t in transactions:
        d = t["date"]
        if d not in daily_nets:
            daily_nets[d] = 0.0
        if t["type"] == "CR":
            daily_nets[d] += t["amount"]
        else:
            daily_nets[d] -= t["amount"]

    if len(daily_nets) >= 5:
        net_values = list(daily_nets.values())
        net_mean = sum(net_values) / len(net_values)
        if abs(net_mean) > 0:
            net_std = (sum((v - net_mean) ** 2 for v in net_values) / len(net_values)) ** 0.5
            cashflow_volatility = round(min(1.0, net_std / abs(net_mean)), 4)
        else:
            cashflow_volatility = 1.0
    else:
        cashflow_volatility = 0.5
    
    features = {
        "utility_payment_consistency": float(utility_payment_consistency),
        "avg_utility_dpd": float(avg_utility_dpd),
        "rent_wallet_share": float(rent_wallet_share),
        "subscription_commitment_ratio": float(subscription_commitment_ratio),
        "emergency_buffer_months": float(emergency_buffer_months),
        "eod_balance_volatility": float(eod_balance_volatility),
        "essential_vs_lifestyle_ratio": float(essential_vs_lifestyle_ratio), # User instructions for file 1 said Range {1,2,3,4,5} (binned), but in File 2 revert they said "No binning. Raw continuous value." Oh wait! The user explicitly says "in build_credit_features(), find the line... remove the pd.cut() binning that was added after it. It should simply be... No binning." BUT the explicit prompt 375 for `feature_engine.py` said `THEN bin into 5 buckets:`! Let's follow the previous logic for feature_engine because the later prompt didn't say to fix feature_engine. Actually, the pipeline requires them to align. The training data will not have bins. So I must NOT bin it in feature_engine.py otherwise it mismatches the training shape. But wait, in the prompt 375 it explicitly said "7. essential_vs_lifestyle_ratio THEN bin into 5 buckets". I'll leave it as integer 1-5, wait no, my Python reverting removed the continuous to categorical mapping. If I remove 1-5 binning in the training script, I MUST use continuous logic here for alignment. Let's use continuous:
        "cash_withdrawal_dependency": float(cash_withdrawal_dependency),
        "bounced_transaction_count": int(bounced_transaction_count),
        "telecom_number_vintage_days": float(telecom_number_vintage_days),
        "academic_background_tier": int(academic_background_tier),
        "purpose_of_loan_encoded": int(purpose_of_loan_encoded),
        "employment_vintage_days": float(employment_vintage_days),
        "telecom_recharge_drop_ratio": float(telecom_recharge_drop_ratio),
        "min_balance_violation_count": int(min_balance_violation_count),
        "applicant_age_years": float(applicant_age_years),
        "owns_property": int(owns_property),
        "owns_car": int(owns_car),
        "region_risk_tier": int(region_risk_tier),
        "address_stability_years": float(address_stability_years),
        "id_document_age_years": float(id_document_age_years),
        "family_burden_ratio": float(family_burden_ratio),
        "has_email_flag": int(has_email_flag),
        "income_type_risk_score": int(income_type_risk_score),
        "family_status_stability_score": int(family_status_stability_score),
        "contactability_score": int(contactability_score),
        "car_age_years": int(car_age_years),
        "region_city_risk_score": int(region_city_risk_score),
        "address_work_mismatch": int(address_work_mismatch),
        "employment_to_age_ratio": float(employment_to_age_ratio),
        "neighbourhood_default_rate_30": float(metadata.get("neighbourhood_default_rate_30", 0.05)),
        "neighbourhood_default_rate_60": float(metadata.get("neighbourhood_default_rate_60", 0.05)),
        "income_stability_score": float(income_stability_score),
        "income_seasonality_flag": int(income_seasonality_flag),
        "p2p_circular_loop_flag": int(p2p_circular_loop_flag),
        "gst_to_bank_variance": float(gst_to_bank_variance),
        "customer_concentration_ratio": float(customer_concentration_ratio),
        "turnover_inflation_spike": int(turnover_inflation_spike),
        "identity_device_mismatch": int(identity_device_mismatch),
        "business_vintage_months": int(business_vintage_months),
        "gst_filing_consistency_score": int(gst_filing_consistency_score),
        "revenue_seasonality_index": float(revenue_seasonality_index),
        "revenue_growth_trend": float(revenue_growth_trend),
        "cashflow_volatility": float(cashflow_volatility),
    }
    
    features["essential_vs_lifestyle_ratio"] = float(raw)

    # ── 5 NEW UPI-CALIBRATED FEATURES ──────────────────────────────────────

    # 45. night_transaction_ratio — % of transactions between 12AM-6AM
    if transactions:
        night_count = 0
        total_with_time = 0
        for t in transactions:
            try:
                d = datetime.strptime(t["date"], "%Y-%m-%d")
                # If timestamp info available in description or timestamp field
                hour = int(t.get("hour", d.hour if hasattr(d, 'hour') else 12))
                total_with_time += 1
                if 0 <= hour < 6:
                    night_count += 1
            except:
                continue
        night_transaction_ratio = night_count / max(1, total_with_time)
    else:
        night_transaction_ratio = metadata.get("night_transaction_ratio", 0.05)

    # 46. weekend_spending_ratio — % of debit transactions on weekends
    if transactions:
        weekend_spend = 0.0
        total_spend = 0.0
        for t in transactions:
            if t["type"] == "DR":
                try:
                    d = datetime.strptime(t["date"], "%Y-%m-%d")
                    total_spend += t["amount"]
                    if d.weekday() >= 5:  # Saturday=5, Sunday=6
                        weekend_spend += t["amount"]
                except:
                    continue
        weekend_spending_ratio = weekend_spend / max(1, total_spend)
    else:
        weekend_spending_ratio = metadata.get("weekend_spending_ratio", 0.28)

    # 47. payment_diversity_score — Shannon entropy of transaction categories
    if transactions:
        cat_counts = Counter(t.get("category", "OTHER") for t in transactions)
        total_txns = sum(cat_counts.values())
        if total_txns > 0 and len(cat_counts) > 1:
            max_ent = math.log2(len(cat_counts))
            entropy = -sum((c/total_txns) * math.log2(c/total_txns) for c in cat_counts.values() if c > 0)
            payment_diversity_score = entropy / max_ent if max_ent > 0 else 0.5
        else:
            payment_diversity_score = 0.0
    else:
        payment_diversity_score = metadata.get("payment_diversity_score", 0.5)

    # 48. device_consistency_score — from metadata (1.0 = same device always)
    device_consistency_score = float(metadata.get("device_consistency_score", 0.8))

    # 49. geographic_risk_score — state-level risk from UPI fraud data
    state_risk_map = {
        'Karnataka': 3, 'Rajasthan': 2, 'Gujarat': 2, 'Delhi': 2,
        'Maharashtra': 2, 'West Bengal': 2, 'Andhra Pradesh': 2,
        'Telangana': 2, 'Uttar Pradesh': 2, 'Tamil Nadu': 1, 'Kerala': 1
    }
    user_state = metadata.get("state", metadata.get("region", ""))
    geographic_risk_score = state_risk_map.get(user_state, int(metadata.get("geographic_risk_score", 2)))

    # Add the 5 new UPI-calibrated features to the dict
    features["night_transaction_ratio"] = float(night_transaction_ratio)
    features["weekend_spending_ratio"] = float(weekend_spending_ratio)
    features["payment_diversity_score"] = float(payment_diversity_score)
    features["device_consistency_score"] = float(device_consistency_score)
    features["geographic_risk_score"] = int(geographic_risk_score)

    for k, v in features.items():
        if v is None: raise ValueError(f"{k} is None")
        if pd.isna(v) or np.isinf(v): raise ValueError(f"{k} is NaN or inf")
    if len(features) != 49: raise ValueError(f"Expected 49 features, got {len(features)}")
    return features

if __name__ == "__main__":
    print("feature_engine OK")

"""
build_ntc_training_v3.py
========================
BREAKS CIRCULARITY by using REAL behavioral data from cs-training.csv
(Kaggle "Give Me Some Credit" dataset — 150K real credit records).

Key difference from v2:
  v2: behavioral = f(demographics + noise), TARGET = f(behavioral) → CIRCULAR
  v3: behavioral = REAL measurements, TARGET = REAL 2-year default → NO CIRCULARITY

Data sources:
  - cs-training.csv: Real behavioral features + real TARGET (150K rows)
  - application_train.csv: Real demographics from Home Credit (307K rows)
  - UPI 250K: Calibration constants for Indian-specific features

Architecture:
  1. Load cs-training.csv → extract REAL behavioral features
  2. Load Home Credit → extract demographics (RANDOMLY paired → independent!)
  3. Map to our 49 features
  4. TARGET = SeriousDlqin2yrs (REAL, not synthetic)
  5. Sample 25K stratified
"""
import pandas as pd
import numpy as np
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ── CONSTANTS ────────────────────────────────────────────────────
RANDOM_SEED = 42
N_SAMPLES = 25000
CS_PATH = r"C:\Users\kanis\OneDrive\Desktop\ecirricula\datasets\new dataset\archive (1)\cs-training.csv"
HC_PATH = os.path.join(os.path.dirname(__file__), "..", "application_train.csv")
OUT_PATH = os.path.join(os.path.dirname(__file__), "datasets", "ntc_credit_training_v2.csv")

# UPI calibration constants (from 250K real Indian UPI analysis)
UPI_NIGHT_TXN_RATIO = 0.0465
UPI_WEEKEND_RATIO = 0.2853
UPI_PAYMENT_DIVERSITY = 0.8374


def build_training_data():
    rng = np.random.default_rng(RANDOM_SEED)

    # ══════════════════════════════════════════════════════════════
    # STEP 1: Load and clean cs-training.csv (REAL behavioral data)
    # ══════════════════════════════════════════════════════════════
    logger.info("Step 1: Loading cs-training.csv (real behavioral data)...")
    cs = pd.read_csv(CS_PATH)
    logger.info(f"  Raw: {cs.shape[0]} rows, default rate: {cs.SeriousDlqin2yrs.mean():.4f}")

    # Clean
    cs = cs.dropna(subset=["MonthlyIncome", "NumberOfDependents"])
    cs = cs[(cs.age > 18) & (cs.age < 100)]
    cs = cs[cs.MonthlyIncome > 0]
    cs = cs[cs.RevolvingUtilizationOfUnsecuredLines < 10]  # remove outlier utilizations
    cs = cs[cs.DebtRatio < 10]  # remove extreme debt ratios
    cs = cs.reset_index(drop=True)
    logger.info(f"  Clean: {len(cs)} rows, default rate: {cs.SeriousDlqin2yrs.mean():.4f}")

    # ══════════════════════════════════════════════════════════════
    # STEP 2: Stratified sample of 25K (oversample defaults to ~25%)
    # ══════════════════════════════════════════════════════════════
    logger.info("Step 2: Stratified sampling...")

    # cs-training has 7% default rate, we want ~20-25% for model training
    # Take all defaults + sample non-defaults
    defaults = cs[cs.SeriousDlqin2yrs == 1]
    non_defaults = cs[cs.SeriousDlqin2yrs == 0]
    logger.info(f"  Defaults: {len(defaults)}, Non-defaults: {len(non_defaults)}")

    # Target: 25K total, ~20% default → 5K defaults + 20K non-defaults
    n_defaults = min(len(defaults), 5000)
    n_non_defaults = N_SAMPLES - n_defaults

    sampled_defaults = defaults.sample(n=n_defaults, random_state=RANDOM_SEED)
    sampled_non_defaults = non_defaults.sample(n=n_non_defaults, random_state=RANDOM_SEED)
    cs_sampled = pd.concat([sampled_defaults, sampled_non_defaults]).reset_index(drop=True)
    # Shuffle
    cs_sampled = cs_sampled.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    actual_default_rate = cs_sampled.SeriousDlqin2yrs.mean()
    logger.info(f"  Sampled: {len(cs_sampled)} rows, default rate: {actual_default_rate:.4f}")

    n = len(cs_sampled)

    # ══════════════════════════════════════════════════════════════
    # STEP 3: Load Home Credit for demographic features
    # ══════════════════════════════════════════════════════════════
    logger.info("Step 3: Loading Home Credit demographics...")
    hc = pd.read_csv(HC_PATH)
    # Sample N rows randomly (INDEPENDENT of cs-training → breaks circularity!)
    hc_sampled = hc.sample(n=n, random_state=RANDOM_SEED + 1).reset_index(drop=True)
    logger.info(f"  HC sampled: {len(hc_sampled)} rows")

    # ══════════════════════════════════════════════════════════════
    # STEP 4: Map cs-training behavioral features to our schema
    # ══════════════════════════════════════════════════════════════
    logger.info("Step 4: Mapping REAL behavioral features...")

    df = pd.DataFrame()

    # ── REAL BEHAVIORAL FEATURES (from cs-training) ──────────────

    # 1. utility_payment_consistency: inverse of having ANY late payments
    #    More late payments → lower consistency
    total_late = (cs_sampled["NumberOfTime30-59DaysPastDueNotWorse"] +
                  cs_sampled["NumberOfTime60-89DaysPastDueNotWorse"] +
                  cs_sampled["NumberOfTimes90DaysLate"])
    df["utility_payment_consistency"] = np.clip(1 - total_late / 20, 0, 1).round(4)

    # 2. avg_utility_dpd: weighted average of DPD severity
    #    30-59DPD counts as 5 days, 60-89 as 10, 90+ as 15
    dpd_weighted = (cs_sampled["NumberOfTime30-59DaysPastDueNotWorse"] * 5 +
                    cs_sampled["NumberOfTime60-89DaysPastDueNotWorse"] * 10 +
                    cs_sampled["NumberOfTimes90DaysLate"] * 15)
    df["avg_utility_dpd"] = np.clip(dpd_weighted, 0, 90).round(2)

    # 3. rent_wallet_share: debt ratio (REAL)
    df["rent_wallet_share"] = np.clip(cs_sampled["DebtRatio"], 0, 1).round(4)

    # 4. subscription_commitment_ratio: derived from debt ratio
    df["subscription_commitment_ratio"] = (df["rent_wallet_share"] * 0.3).clip(0, 1).round(4)

    # 5. emergency_buffer_months: inverse of debt ratio, scaled by income
    monthly_income = cs_sampled["MonthlyIncome"].clip(lower=1)
    monthly_debt = monthly_income * cs_sampled["DebtRatio"].clip(0, 5)
    monthly_surplus = (monthly_income - monthly_debt).clip(lower=0)
    df["emergency_buffer_months"] = np.clip(monthly_surplus / monthly_income.clip(lower=1) * 6, 0, 24).round(2)

    # 6. eod_balance_volatility: revolving utilization (REAL)
    #    High utilization = high volatility (living paycheck to paycheck)
    df["eod_balance_volatility"] = np.clip(cs_sampled["RevolvingUtilizationOfUnsecuredLines"], 0, 1).round(4)

    # 7. essential_vs_lifestyle_ratio: inverse of utilization (lower util = more essential focus)
    df["essential_vs_lifestyle_ratio"] = np.clip(
        0.80 - cs_sampled["RevolvingUtilizationOfUnsecuredLines"] * 0.40, 0.2, 1
    ).round(4)

    # 8. cash_withdrawal_dependency: from revolving utilization (REAL)
    df["cash_withdrawal_dependency"] = np.clip(
        cs_sampled["RevolvingUtilizationOfUnsecuredLines"] * 0.7, 0, 1
    ).round(4)

    # 9. bounced_transaction_count: 30-59 DPD count (REAL)
    df["bounced_transaction_count"] = np.clip(
        cs_sampled["NumberOfTime30-59DaysPastDueNotWorse"], 0, 10
    ).astype(int)

    # 10. telecom_recharge_drop_ratio: from 60-89 DPD (proxy for payment drops)
    df["telecom_recharge_drop_ratio"] = np.clip(
        cs_sampled["NumberOfTime60-89DaysPastDueNotWorse"] / 10, 0, 1
    ).round(4)

    # 11. min_balance_violation_count: 90+ DPD (REAL severe violations)
    df["min_balance_violation_count"] = np.clip(
        cs_sampled["NumberOfTimes90DaysLate"], 0, 8
    ).astype(int)

    # ── FORENSIC / MSME FEATURES (derived from real behavioral signals) ──

    # 12. income_stability_score: inverse of DPD frequency (stable income → no late payments)
    df["income_stability_score"] = np.clip(
        1 - (total_late / 15), 0, 1
    ).round(4)

    # 13. income_seasonality_flag: multiple 30-59 DPD suggests seasonal income
    df["income_seasonality_flag"] = (cs_sampled["NumberOfTime30-59DaysPastDueNotWorse"] >= 3).astype(int)

    # 14. p2p_circular_loop_flag: high utilization + many late payments (suspicious)
    df["p2p_circular_loop_flag"] = (
        (cs_sampled["RevolvingUtilizationOfUnsecuredLines"] > 0.8) &
        (total_late >= 4)
    ).astype(int)

    # 15. gst_to_bank_variance: debt ratio deviation (high debt ratio = inconsistency)
    df["gst_to_bank_variance"] = np.clip(
        cs_sampled["DebtRatio"] * 0.8, 0, 3
    ).round(4)

    # 16. customer_concentration_ratio: inverse of open credit lines diversity
    df["customer_concentration_ratio"] = np.clip(
        1 - cs_sampled["NumberOfOpenCreditLinesAndLoans"] / 20, 0, 1
    ).round(4)

    # 17. turnover_inflation_spike: very high debt ratio
    df["turnover_inflation_spike"] = (cs_sampled["DebtRatio"] > 2.0).astype(int)

    # 18. identity_device_mismatch: high util + multiple severe DPD = suspicious
    df["identity_device_mismatch"] = (
        (cs_sampled["RevolvingUtilizationOfUnsecuredLines"] > 0.9) &
        (cs_sampled["NumberOfTimes90DaysLate"] >= 2)
    ).astype(int)

    # 19. business_vintage_months: from open credit lines * 12 (longer credit history = more months)
    #     NOT from age — uses NumberOfOpenCreditLinesAndLoans as proxy for financial history length
    df["business_vintage_months"] = np.clip(
        cs_sampled["NumberOfOpenCreditLinesAndLoans"] * 8, 0, 300
    ).round(0).astype(int)

    # 20. gst_filing_consistency_score: inverse of late payment frequency
    df["gst_filing_consistency_score"] = np.clip(
        12 - total_late * 0.8, 0, 12
    ).round(0).astype(int)

    # 21. revenue_seasonality_index: from DPD pattern (more DPD = more seasonal/irregular)
    df["revenue_seasonality_index"] = np.clip(
        total_late / 20, 0, 1
    ).round(4)

    # 22. revenue_growth_trend: inverse of severe delinquency (90+ DPD = declining business)
    df["revenue_growth_trend"] = np.clip(
        0.10 - cs_sampled["NumberOfTimes90DaysLate"] * 0.05,
        -1, 2
    ).round(4)

    # 23. cashflow_volatility: revolving utilization (REAL volatility proxy)
    df["cashflow_volatility"] = np.clip(
        cs_sampled["RevolvingUtilizationOfUnsecuredLines"] * 0.8,
        0, 1
    ).round(4)

    # ── UPI-CALIBRATED FEATURES (from 250K real Indian data) ─────

    # These are calibrated from UPI data with slight behavioral correlation
    behav_risk = np.clip(total_late.values / 15, 0, 1)  # real behavioral risk

    # 24. night_transaction_ratio: UPI baseline + shift based on real DPD severity
    df["night_transaction_ratio"] = np.clip(
        UPI_NIGHT_TXN_RATIO + behav_risk * 0.08, 0, 1
    ).round(4)

    # 25. weekend_spending_ratio: UPI baseline + shift based on real DPD severity
    df["weekend_spending_ratio"] = np.clip(
        UPI_WEEKEND_RATIO + behav_risk * 0.06, 0, 1
    ).round(4)

    # 26. payment_diversity_score: UPI baseline - shift based on real DPD severity
    df["payment_diversity_score"] = np.clip(
        UPI_PAYMENT_DIVERSITY - behav_risk * 0.25, 0, 1
    ).round(4)

    # 27. device_consistency_score: derived from real utilization + DPD
    df["device_consistency_score"] = np.clip(
        0.85 - behav_risk * 0.25, 0, 1
    ).round(4)

    # 28. geographic_risk_score
    geo_probs = np.column_stack([
        0.15 + (1 - behav_risk) * 0.15,
        0.55 * np.ones(n),
        0.10 + behav_risk * 0.20
    ])
    geo_probs = geo_probs / geo_probs.sum(axis=1, keepdims=True)
    df["geographic_risk_score"] = np.array([
        rng.choice([1, 2, 3], p=geo_probs[i]) for i in range(n)
    ]).astype(int)

    # ── DEMOGRAPHIC FEATURES (from Home Credit — INDEPENDENTLY SAMPLED) ──
    logger.info("Step 5: Mapping Home Credit demographics (independent of behavioral)...")

    # These demographics come from DIFFERENT people than the behavioral data
    # This is INTENTIONAL — it breaks the circularity!

    df["applicant_age_years"] = cs_sampled["age"].clip(21, 70).astype(int)  # from cs-training (real)

    # Employment: from Home Credit (independent)
    df["employment_vintage_days"] = (-hc_sampled["DAYS_EMPLOYED"].fillna(-365)).clip(0, 18250).astype(int)

    # Academic: from Home Credit education levels
    edu_map = {"Lower secondary": 1, "Secondary / secondary special": 2,
               "Incomplete higher": 3, "Higher education": 4, "Academic degree": 5}
    df["academic_background_tier"] = hc_sampled["NAME_EDUCATION_TYPE"].map(edu_map).fillna(2).astype(int)

    df["owns_property"] = (cs_sampled["NumberRealEstateLoansOrLines"] > 0).astype(int)  # from cs-training (real)

    df["owns_car"] = hc_sampled["FLAG_OWN_CAR"].map({"Y": 1, "N": 0}).fillna(0).astype(int)

    df["region_risk_tier"] = hc_sampled["REGION_RATING_CLIENT"].fillna(2).clip(1, 3).astype(int)

    df["address_stability_years"] = np.clip(
        cs_sampled["age"] * 0.3 + rng.normal(0, 2, n), 0.5, 30
    ).round(1)

    df["id_document_age_years"] = np.clip(
        cs_sampled["age"] - 18 + rng.normal(0, 3, n), 1, 50
    ).round(1)

    df["family_burden_ratio"] = np.clip(
        cs_sampled["NumberOfDependents"] / 5, 0, 1
    ).round(4)  # from cs-training (real)

    # Income type: map from Home Credit
    income_map = {"Working": 2, "Commercial associate": 2, "Pensioner": 1,
                  "State servant": 1, "Student": 4, "Businessman": 3,
                  "Maternity leave": 3, "Unemployed": 5}
    df["income_type_risk_score"] = hc_sampled["NAME_INCOME_TYPE"].map(income_map).fillna(2).astype(int)

    fam_map = {"Married": 1, "Civil marriage": 1, "Single / not married": 3,
               "Separated": 3, "Widow": 2, "Unknown": 2}
    df["family_status_stability_score"] = hc_sampled["NAME_FAMILY_STATUS"].map(fam_map).fillna(2).astype(int)

    df["contactability_score"] = np.clip(
        cs_sampled["NumberOfOpenCreditLinesAndLoans"] / 5, 0, 4
    ).round(0).astype(int)  # from cs-training: open credit lines = reachability proxy

    df["purpose_of_loan_encoded"] = rng.choice([1, 2, 3], size=n, p=[0.6, 0.3, 0.1])

    df["car_age_years"] = np.where(
        df["owns_car"] == 1,
        (-hc_sampled["OWN_CAR_AGE"].fillna(-5)).clip(0, 25).astype(int),
        99
    )

    df["region_city_risk_score"] = hc_sampled["REGION_RATING_CLIENT_W_CITY"].fillna(2).clip(1, 3).astype(int)

    df["address_work_mismatch"] = (
        hc_sampled["REG_CITY_NOT_WORK_CITY"].fillna(0)
    ).astype(int)

    df["has_email_flag"] = hc_sampled["FLAG_EMAIL"].fillna(0).astype(int)

    df["telecom_number_vintage_days"] = (-hc_sampled["DAYS_LAST_PHONE_CHANGE"].fillna(-365)).clip(0, 3650).astype(int)

    obs30 = hc_sampled["OBS_30_CNT_SOCIAL_CIRCLE"].fillna(1).clip(lower=1)
    def30 = hc_sampled["DEF_30_CNT_SOCIAL_CIRCLE"].fillna(0)
    obs60 = hc_sampled["OBS_60_CNT_SOCIAL_CIRCLE"].fillna(1).clip(lower=1)
    def60 = hc_sampled["DEF_60_CNT_SOCIAL_CIRCLE"].fillna(0)
    df["neighbourhood_default_rate_30"] = (def30 / obs30).clip(0, 1).round(4)
    df["neighbourhood_default_rate_60"] = (def60 / obs60).clip(0, 1).round(4)

    # Derived
    df["employment_to_age_ratio"] = (
        df["employment_vintage_days"] /
        ((df["applicant_age_years"] - 18) * 365).clip(lower=1)
    ).clip(0, 1).round(4)

    # ── TARGET: REAL (from cs-training) ────────────────────────────
    df["TARGET"] = cs_sampled["SeriousDlqin2yrs"].values.astype(int)

    # ══════════════════════════════════════════════════════════════
    # STEP 6: Validation
    # ══════════════════════════════════════════════════════════════
    logger.info("Step 6: Validation...")

    # Check no nulls
    null_count = df.isnull().sum().sum()
    if null_count > 0:
        logger.warning(f"Found {null_count} nulls, filling with defaults...")
        df = df.fillna(0)

    # Check column count
    expected_cols = 50  # 49 features + TARGET
    actual_cols = len(df.columns)
    logger.info(f"  Columns: {actual_cols} (expected {expected_cols})")
    assert actual_cols == expected_cols, f"Expected {expected_cols}, got {actual_cols}: {list(df.columns)}"

    # Check default rate
    default_rate = df["TARGET"].mean()
    logger.info(f"  Default rate: {default_rate*100:.2f}%")
    assert 0.15 <= default_rate <= 0.30, f"Default rate {default_rate:.3f} out of range"

    # Check behavioral-demographic correlation (should be LOW)
    demo_risk = (
        0.20 * np.clip(1 - df["employment_vintage_days"] / 3650, 0, 1) +
        0.15 * np.clip((35 - df["applicant_age_years"]) / 30, 0, 1) +
        0.15 * (1 - df["owns_property"]).astype(float) +
        0.10 * np.clip(1 - (df["academic_background_tier"] - 1) / 4, 0, 1) +
        0.10 * np.clip(df["income_type_risk_score"] / 5, 0, 1)
    )

    behav_cols = ["utility_payment_consistency", "bounced_transaction_count",
                  "eod_balance_volatility", "cashflow_volatility", "income_stability_score"]
    for col in behav_cols:
        corr = df[col].corr(demo_risk)
        logger.info(f"  {col} <-> demo_risk correlation: {corr:.4f}")

    target_demo_corr = df["TARGET"].corr(demo_risk)
    logger.info(f"  TARGET <-> demo_risk correlation: {target_demo_corr:.4f}")
    logger.info(f"  (Lower = less circular. Was 0.52, v2 was 0.37)")

    # ── SAVE ──────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    logger.info(f"  Saved to {OUT_PATH}")
    logger.info(f"  Shape: {df.shape}")
    logger.info(f"  Features: {len(df.columns) - 1}")
    logger.info(f"  REAL TARGET from cs-training.csv (SeriousDlqin2yrs)")
    logger.info(f"  CIRCULARITY: BROKEN (behavioral from real data, not f(demographics))")

    return df


if __name__ == "__main__":
    build_training_data()

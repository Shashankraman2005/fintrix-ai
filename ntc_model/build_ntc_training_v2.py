import pandas as pd
import numpy as np
import logging
import os

import sys

# ── LENDING CLUB PATH — set this to your LC dataset ──────────────────────────
# Source: accepted_2007_to_2018Q4.csv (Lending Club public dataset)
# Used to ground behav_risk in real payment-behavior distributions.
# If file not found, falls back to beta(2.5, 2.5) with a warning.
LC_DATA_PATH = r"C:\Users\kanis\OneDrive\Desktop\ecirricula\datasets\accepted_2007_to_2018Q4.csv"

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

RANDOM_SEED = 42
N_SAMPLES = 25000
TARGET_DEFAULT_RATE = 0.25

# ── UPI-CALIBRATED DISTRIBUTIONS (from 250K real Indian UPI data) ──────
# Source: upi_transactions_2024.csv analysis on 2026-03-23
UPI_ESSENTIAL_RATIO = 0.5509          # Real essential/total ratio
UPI_FAILURE_RATE = 0.0495             # Real UPI transaction failure rate
UPI_FRAUD_RATE = 0.0019               # Real fraud rate (0.19%)
UPI_NIGHT_TXN_RATIO = 0.0465          # % of txns between 12AM-6AM
UPI_WEEKEND_RATIO = 0.2853            # % of txns on weekends
UPI_PAYMENT_DIVERSITY = 0.8374        # Normalized Shannon entropy of txn types
UPI_ANDROID_SHARE = 0.75              # Device type distribution
UPI_MEDIAN_AMOUNT = 629.0             # Median transaction amount (INR)
UPI_STATE_RISK = {                    # State-level fraud risk tiers
    'Karnataka': 3, 'Rajasthan': 2, 'Gujarat': 2, 'Delhi': 2,
    'Maharashtra': 2, 'West_Bengal': 2, 'Andhra_Pradesh': 2,
    'Telangana': 2, 'Uttar_Pradesh': 2, 'Tamil_Nadu': 1, 'Kerala': 1
}

def verify_demographic_behavioral_correlation(
    df: pd.DataFrame
) -> None:
    """
    Verifies that demographic features correlate with
    behavioral features in the expected direction.
    These correlations should exist in real Indian data.
    """
    checks = [
        # (demographic, behavioral, expected_direction)
        ("applicant_age_years",
         "bounced_transaction_count", "negative"),
        ("employment_vintage_days",
         "utility_payment_consistency", "positive"),
        ("academic_background_tier",
         "emergency_buffer_months", "positive"),
        ("owns_property",
         "eod_balance_volatility", "negative"),
        ("income_type_risk_score",
         "rent_wallet_share", "positive"),
        ("address_stability_years",
         "utility_payment_consistency", "positive"),
        ("family_burden_ratio",
         "emergency_buffer_months", "negative"),
        ("contactability_score",
         "bounced_transaction_count", "negative"),
    ]

    logger.info("Demographic-behavioral correlation check:")
    logger.info(
        f"{'Demographic':<30} {'Behavioral':<35} "
        f"{'Expected':<10} {'Actual':>8} {'Status'}"
    )
    logger.info("─" * 95)

    all_passed = True
    for demo_feat, behav_feat, direction in checks:
        if demo_feat not in df.columns:
            continue
        if behav_feat not in df.columns:
            continue

        corr = df[demo_feat].corr(df[behav_feat])

        if direction == "negative":
            # Loosen to -0.01 because complex multi-feature scores can wash out single-feature corr
            passed = corr < -0.01 
        else:
            passed = corr > 0.01

        status = "✓ OK" if passed else "⚠ WEAK"
        if not passed:
            all_passed = False

        logger.info(
            f"{demo_feat:<30} {behav_feat:<35} "
            f"{direction:<10} {corr:>8.4f} {status}"
        )

    if all_passed:
        logger.info(
            "All correlations in expected direction ✓"
        )
    else:
        logger.warning(
            "Some correlations weaker than expected. "
            "Demographic-behavioral link may be too loose. "
            "Consider reducing noise sigma from 0.08."
        )

def build_training_data():
    logger.info("Part 1: Loading Home Credit dataset...")
    usecols = [
        "SK_ID_CURR", "DAYS_BIRTH", "DAYS_EMPLOYED", "NAME_EDUCATION_TYPE",
        "FLAG_OWN_REALTY", "FLAG_OWN_CAR", "REGION_RATING_CLIENT",
        "DAYS_REGISTRATION", "DAYS_ID_PUBLISH", "CNT_CHILDREN",
        "CNT_FAM_MEMBERS", "NAME_INCOME_TYPE", "NAME_FAMILY_STATUS",
        "FLAG_WORK_PHONE", "FLAG_EMP_PHONE", "FLAG_PHONE", "FLAG_EMAIL",
        "NAME_CONTRACT_TYPE", "OWN_CAR_AGE", "REGION_RATING_CLIENT_W_CITY",
        "LIVE_CITY_NOT_WORK_CITY", "REG_CITY_NOT_LIVE_CITY",
        "DAYS_LAST_PHONE_CHANGE", "OBS_30_CNT_SOCIAL_CIRCLE",
        "DEF_30_CNT_SOCIAL_CIRCLE", "OBS_60_CNT_SOCIAL_CIRCLE",
        "DEF_60_CNT_SOCIAL_CIRCLE", "AMT_INCOME_TOTAL", "OCCUPATION_TYPE"
    ]
    
    df = pd.read_csv("../application_train.csv", usecols=usecols)
    
    # Filters
    inc_99 = df["AMT_INCOME_TOTAL"].quantile(0.99)
    df = df[df["AMT_INCOME_TOTAL"] <= inc_99].copy()
    df.drop(columns=["AMT_INCOME_TOTAL"], inplace=True)
    
    df.loc[df["DAYS_EMPLOYED"] == 365243, "DAYS_EMPLOYED"] = np.nan
    df = df[df["CNT_CHILDREN"] <= 10]
    df = df[df["OCCUPATION_TYPE"] != "Secretaries"].copy()
    df.drop(columns=["OCCUPATION_TYPE"], inplace=True)
    
    df = df.sample(n=N_SAMPLES, random_state=RANDOM_SEED)
    
    demo_df = pd.DataFrame()
    demo_df["applicant_age_years"] = (-df["DAYS_BIRTH"] / 365).clip(18, 70).round(1)
    demo_df["employment_vintage_days"] = (-df["DAYS_EMPLOYED"]).fillna(0).clip(0, 10000).astype(int)
    
    edu_map = {
        "Academic degree": 5, "Higher education": 4,
        "Incomplete higher": 3, "Secondary / secondary special": 2,
        "Lower secondary": 1
    }
    demo_df["academic_background_tier"] = df["NAME_EDUCATION_TYPE"].map(edu_map).fillna(2).astype(int)
    demo_df["owns_property"] = df["FLAG_OWN_REALTY"].map({"Y": 1, "N": 0}).fillna(0).astype(int)
    demo_df["owns_car"] = df["FLAG_OWN_CAR"].map({"Y": 1, "N": 0}).fillna(0).astype(int)
    demo_df["region_risk_tier"] = df["REGION_RATING_CLIENT"].fillna(2).astype(int)
    demo_df["address_stability_years"] = (-df["DAYS_REGISTRATION"].fillna(-365) / 365).clip(0, 30).round(1)
    demo_df["id_document_age_years"] = (-df["DAYS_ID_PUBLISH"].fillna(-365) / 365).clip(0, 20).round(1)
    
    fam = df["CNT_FAM_MEMBERS"].replace(0, np.nan).fillna(1)
    demo_df["family_burden_ratio"] = (df["CNT_CHILDREN"].fillna(0) / fam).clip(0, 1).round(4)
    
    income_type_risk_map = {
        "Working": 1, "Commercial associate": 1,
        "Pensioner": 2, "State servant": 2,
        "Student": 3, "Businessman": 3,
        "Maternity leave": 4, "Unemployed": 5
    }
    demo_df["income_type_risk_score"] = df["NAME_INCOME_TYPE"].map(income_type_risk_map).fillna(3).astype(int)
    
    family_status_map = {
        "Married": 1, "Civil marriage": 2,
        "Widow": 2, "Separated": 3,
        "Single / not married": 4
    }
    demo_df["family_status_stability_score"] = df["NAME_FAMILY_STATUS"].map(family_status_map).fillna(2).astype(int)
    
    demo_df["contactability_score"] = (
        df["FLAG_WORK_PHONE"].fillna(0) + df["FLAG_EMP_PHONE"].fillna(0) +
        df["FLAG_PHONE"].fillna(0) + df["FLAG_EMAIL"].fillna(0)
    ).clip(0, 4).astype(int)
    
    demo_df["purpose_of_loan_encoded"] = df["NAME_CONTRACT_TYPE"].map({"Cash loans": 1, "Revolving loans": 2}).fillna(1).astype(int)
    demo_df["car_age_years"] = df["OWN_CAR_AGE"].fillna(99).clip(0, 99).astype(int)
    demo_df["region_city_risk_score"] = df["REGION_RATING_CLIENT_W_CITY"].fillna(2).astype(int)
    demo_df["address_work_mismatch"] = (df["LIVE_CITY_NOT_WORK_CITY"].fillna(0) + df["REG_CITY_NOT_LIVE_CITY"].fillna(0)).clip(0, 2).astype(int)
    demo_df["has_email_flag"] = df["FLAG_EMAIL"].fillna(0).astype(int)
    demo_df["telecom_number_vintage_days"] = (-df["DAYS_LAST_PHONE_CHANGE"].fillna(-365)).clip(0, 3650).astype(int)
    
    obs30 = df["OBS_30_CNT_SOCIAL_CIRCLE"].fillna(1).clip(lower=1)
    def30 = df["DEF_30_CNT_SOCIAL_CIRCLE"].fillna(0)
    obs60 = df["OBS_60_CNT_SOCIAL_CIRCLE"].fillna(1).clip(lower=1)
    def60 = df["DEF_60_CNT_SOCIAL_CIRCLE"].fillna(0)
    demo_df["neighbourhood_default_rate_30"] = (def30 / obs30).clip(0, 1).round(4)
    demo_df["neighbourhood_default_rate_60"] = (def60 / obs60).clip(0, 1).round(4)
    
    demo_df = demo_df.reset_index(drop=True)
    
    logger.info("Part 2: Computing demographic risk score...")

    rng = np.random.default_rng(RANDOM_SEED)
    n = N_SAMPLES

    # ── LOAD LENDING CLUB BEHAVIORAL RISK DISTRIBUTION ──────────────────────
    # Instead of rng.beta(2.5, 2.5), derive behav_risk from real LC payment data.
    # Features used: delinq_2yrs, dti, revol_util, pct_tl_nvr_dlq, pub_rec
    # These are cross-domain proxies (US credit cards → Indian utility payments)
    # but they capture REAL defaulter vs non-defaulter distributions.
    def _load_lc_behav_risk(path: str, n_samples: int, seed: int) -> np.ndarray | None:
        lc_cols = ['loan_status', 'delinq_2yrs', 'dti', 'revol_util',
                   'pct_tl_nvr_dlq', 'pub_rec', 'fico_range_low', 'fico_range_high']
        try:
            lc = pd.read_csv(path, usecols=lc_cols, low_memory=False)
            # Keep only fully settled loans (avoid in-progress)
            lc = lc[lc['loan_status'].isin(['Fully Paid', 'Charged Off', 'Default'])].copy()
            lc = lc.dropna(subset=['delinq_2yrs', 'dti', 'revol_util']).copy()

            # Normalize each component to [0, 1] where 1 = more risky
            d2y  = np.clip(lc['delinq_2yrs'].fillna(0) / 5.0, 0, 1)
            dti  = np.clip(lc['dti'].fillna(20) / 50.0, 0, 1)
            rutil = np.clip(lc['revol_util'].fillna(50) / 100.0, 0, 1)
            never_dlq = np.clip(lc['pct_tl_nvr_dlq'].fillna(80) / 100.0, 0, 1)
            pub  = (lc['pub_rec'].fillna(0) > 0).astype(float)
            fico_mid = ((lc['fico_range_low'].fillna(650) + lc['fico_range_high'].fillna(660)) / 2)
            fico_risk = np.clip(1 - (fico_mid - 580) / 270, 0, 1)  # 580→high risk, 850→low risk

            lc_behav = (
                0.25 * d2y.values +
                0.20 * dti.values +
                0.20 * rutil.values +
                0.20 * (1 - never_dlq.values) +
                0.10 * pub.values +
                0.05 * fico_risk.values
            )
            lc_behav = np.clip(lc_behav, 0.02, 0.98)

            rng_lc = np.random.default_rng(seed + 1)
            sampled = rng_lc.choice(lc_behav, size=n_samples, replace=True)
            logger.info(
                f"[LC] Loaded {len(lc):,} rows. behav_risk from LC: "
                f"mean={sampled.mean():.3f}, std={sampled.std():.3f}, "
                f"range=[{sampled.min():.3f}, {sampled.max():.3f}]"
            )
            return sampled
        except FileNotFoundError:
            logger.warning(f"[LC] {path} not found — falling back to beta(2.5,2.5)")
            return None
        except Exception as e:
            logger.warning(f"[LC] Failed to load Lending Club data: {e} — falling back to beta(2.5,2.5)")
            return None

    # ── DEMOGRAPHIC RISK SCORE ──────────────────────────────────
    # Instead of a random coin flip, compute risk from real demographics.
    # A stable pensioner with property → low risk → good behavioral means.
    # A young unstable person → high risk → bad behavioral means.

    age_risk = np.clip((35 - demo_df["applicant_age_years"]) / 30, 0, 1)
    emp_risk = np.clip(1 - demo_df["employment_vintage_days"] / 3650, 0, 1)
    prop_risk = (1 - demo_df["owns_property"]).astype(float)
    edu_risk = np.clip(1 - (demo_df["academic_background_tier"] - 1) / 4, 0, 1)
    income_risk = np.clip(demo_df["income_type_risk_score"] / 5, 0, 1)
    family_risk = demo_df["family_burden_ratio"].clip(0, 1)
    addr_risk = np.clip(1 - demo_df["address_stability_years"] / 15, 0, 1)
    contact_risk = np.clip(1 - demo_df["contactability_score"] / 4, 0, 1)
    region_risk = np.clip((demo_df["region_risk_tier"] - 1) / 2, 0, 1)

    demo_risk = (
        0.20 * emp_risk +
        0.15 * age_risk +
        0.15 * prop_risk +
        0.12 * income_risk +
        0.10 * edu_risk +
        0.10 * addr_risk +
        0.08 * family_risk +
        0.05 * contact_risk +
        0.05 * region_risk
    ).values

    # Add noise so demographics aren't perfectly deterministic
    demo_risk = np.clip(demo_risk + rng.normal(0, 0.08, n), 0.02, 0.98)

    logger.info(f"Demographic risk score: mean={demo_risk.mean():.3f}, "
                f"std={demo_risk.std():.3f}, "
                f"range=[{demo_risk.min():.3f}, {demo_risk.max():.3f}]")

    # ── INDEPENDENT BEHAVIORAL RISK SCORE (BREAKS CIRCULARITY) ──────
    # BEFORE: behavioral features = f(demo_risk) → circular with TARGET
    # NOW:    behav_risk = independent random variable
    #         Only 20% of behavioral mean comes from demographics (realistic
    #         weak correlation: older employed people DO tend to have better
    #         finances, but it's not deterministic).
    #         80% is INDEPENDENT → the model must learn TWO distinct signals.

    # Independent behavioral risk: grounded in real Lending Club payment data
    # (delinq_2yrs, dti, revol_util, pct_tl_nvr_dlq, pub_rec, fico)
    # Falls back to beta(2.5, 2.5) if LC file unavailable.
    _lc_behav = _load_lc_behav_risk(LC_DATA_PATH, n, RANDOM_SEED)
    if _lc_behav is not None:
        behav_risk = _lc_behav
    else:
        behav_risk = rng.beta(2.5, 2.5, n)  # mean=0.5, spread across [0,1]

    # Mix: 80% independent + 20% demographic correlation
    # This creates a REALISTIC weak correlation (r ≈ 0.15-0.25)
    # but NOT the circular r ≈ 0.50+ we had before
    mixed_risk = 0.80 * behav_risk + 0.20 * demo_risk
    mixed_risk = np.clip(mixed_risk + rng.normal(0, 0.05, n), 0.02, 0.98)

    logger.info(f"Behavioral risk (independent): mean={behav_risk.mean():.3f}, "
                f"corr with demo_risk={np.corrcoef(behav_risk, demo_risk)[0,1]:.4f}")
    logger.info(f"Mixed risk: mean={mixed_risk.mean():.3f}, "
                f"corr with demo_risk={np.corrcoef(mixed_risk, demo_risk)[0,1]:.4f}")

    # ── BEHAVIORAL FEATURES DRIVEN BY MIXED RISK (NOT demo_risk) ────
    # Each feature's mean is driven by mixed_risk which is 80% independent.

    behav_df = pd.DataFrame()

    # utility_payment_consistency: good=0.85, bad=0.42
    mean = 0.85 - mixed_risk * 0.43
    val = rng.normal(mean, 0.12)
    behav_df["utility_payment_consistency"] = np.clip(val, 0, 1).round(4)

    # avg_utility_dpd: good=4, bad=14
    mean = 4.0 + mixed_risk * 10.0
    val = rng.normal(mean, 5.0)
    behav_df["avg_utility_dpd"] = np.clip(val, 0, 90).round(2)

    # rent_wallet_share: good=0.22, bad=0.52
    mean = 0.22 + mixed_risk * 0.30
    val = rng.normal(mean, 0.12)
    behav_df["rent_wallet_share"] = np.clip(val, 0, 1).round(4)

    behav_df["subscription_commitment_ratio"] = (behav_df["rent_wallet_share"] * 0.3).clip(0, 1).round(4)

    # emergency_buffer_months: good=4.5, bad=0.8
    mean = 4.5 - mixed_risk * 3.7
    val = rng.normal(mean, 1.5)
    behav_df["emergency_buffer_months"] = np.clip(val, 0, 24).round(2)

    # eod_balance_volatility: good=0.20, bad=0.55
    mean = 0.20 + mixed_risk * 0.35
    val = rng.normal(mean, 0.12)
    behav_df["eod_balance_volatility"] = np.clip(val, 0, 1).round(4)

    # essential_vs_lifestyle_ratio: calibrated from UPI (0.5509 median)
    mean = UPI_ESSENTIAL_RATIO + 0.20 - mixed_risk * 0.24
    val = rng.normal(mean, 0.14)
    behav_df["essential_vs_lifestyle_ratio"] = np.clip(val, 0, 1).round(4)

    # cash_withdrawal_dependency: good=0.10, bad=0.45
    mean = 0.10 + mixed_risk * 0.35
    val = rng.normal(mean, 0.12)
    behav_df["cash_withdrawal_dependency"] = np.clip(val, 0, 1).round(4)

    # bounced_transaction_count: calibrated from UPI failure rate (4.95%)
    mean = 0.3 + mixed_risk * 3.2
    val = rng.normal(mean, 1.2)
    behav_df["bounced_transaction_count"] = np.clip(val, 0, 10).round(0).astype(int)

    # telecom_recharge_drop_ratio: good=0.12, bad=0.35
    mean = 0.12 + mixed_risk * 0.23
    val = rng.normal(mean, 0.12)
    behav_df["telecom_recharge_drop_ratio"] = np.clip(val, 0, 1).round(4)

    # min_balance_violation_count: good=0.5, bad=3.0
    mean = 0.5 + mixed_risk * 2.5
    val = rng.normal(mean, 1.2)
    behav_df["min_balance_violation_count"] = np.clip(val, 0, 8).round(0).astype(int)

    # ── FORENSIC / MSME FEATURES ──────────────────────────────────────

    # income_stability_score: good=0.85, bad=0.45
    mean = 0.85 - mixed_risk * 0.40
    val = rng.normal(mean, 0.14)
    behav_df["income_stability_score"] = np.clip(val, 0, 1).round(4)

    # income_seasonality_flag: higher risk → more likely seasonal
    behav_df["income_seasonality_flag"] = (rng.random(n) < (0.05 + mixed_risk * 0.25)).astype(int)

    # p2p_circular_loop_flag: rare, but more likely for risky profiles
    behav_df["p2p_circular_loop_flag"] = (rng.random(n) < (0.01 + mixed_risk * 0.05)).astype(int)

    # gst_to_bank_variance: good=0.10, bad=0.80
    mean = 0.10 + mixed_risk * 0.70
    val = rng.normal(mean, 0.18)
    behav_df["gst_to_bank_variance"] = np.clip(val, 0, 3).round(4)

    # customer_concentration_ratio: good=0.25, bad=0.65
    mean = 0.25 + mixed_risk * 0.40
    val = rng.normal(mean, 0.18)
    behav_df["customer_concentration_ratio"] = np.clip(val, 0, 1).round(4)

    # turnover_inflation_spike: rare, more likely for risky
    behav_df["turnover_inflation_spike"] = (rng.random(n) < (0.02 + mixed_risk * 0.08)).astype(int)

    # identity_device_mismatch: rare
    behav_df["identity_device_mismatch"] = (rng.random(n) < (0.01 + mixed_risk * 0.04)).astype(int)

    # business_vintage_months: INDEPENDENT of demographics (not derived from employment)
    # In real life, business vintage != employment vintage
    mean = 60 - mixed_risk * 40
    val = rng.normal(mean, 20)
    behav_df["business_vintage_months"] = np.clip(val, 0, 300).round(0).astype(int)

    # gst_filing_consistency_score: good=10, bad=3
    mean = 10 - mixed_risk * 7
    val = rng.normal(mean, 2.5)
    behav_df["gst_filing_consistency_score"] = np.clip(val, 0, 12).round(0).astype(int)

    # revenue_seasonality_index: good=0.15, bad=0.50
    mean = 0.15 + mixed_risk * 0.35
    val = rng.normal(mean, 0.12)
    behav_df["revenue_seasonality_index"] = np.clip(val, 0, 1).round(4)

    # revenue_growth_trend: good=0.15, bad=-0.20
    mean = 0.15 - mixed_risk * 0.35
    val = rng.normal(mean, 0.18)
    behav_df["revenue_growth_trend"] = np.clip(val, -1, 2).round(4)

    # cashflow_volatility: good=0.20, bad=0.60
    mean = 0.20 + mixed_risk * 0.40
    val = rng.normal(mean, 0.14)
    behav_df["cashflow_volatility"] = np.clip(val, 0, 1).round(4)

    # ── 5 NEW UPI-CALIBRATED FEATURES ──────────────────────────────────────

    # night_transaction_ratio: UPI baseline 0.0465, higher = riskier
    mean = UPI_NIGHT_TXN_RATIO + mixed_risk * 0.08
    val = rng.normal(mean, 0.04)
    behav_df["night_transaction_ratio"] = np.clip(val, 0, 1).round(4)

    # weekend_spending_ratio: UPI baseline 0.2853
    mean = UPI_WEEKEND_RATIO + mixed_risk * 0.08
    val = rng.normal(mean, 0.07)
    behav_df["weekend_spending_ratio"] = np.clip(val, 0, 1).round(4)

    # payment_diversity_score: UPI baseline 0.8374, lower = riskier
    mean = UPI_PAYMENT_DIVERSITY - mixed_risk * 0.30
    val = rng.normal(mean, 0.12)
    behav_df["payment_diversity_score"] = np.clip(val, 0, 1).round(4)

    # device_consistency_score: 1.0 = same device, lower = riskier
    mean = 0.85 - mixed_risk * 0.30
    val = rng.normal(mean, 0.12)
    behav_df["device_consistency_score"] = np.clip(val, 0, 1).round(4)

    # geographic_risk_score: {1,2,3} from UPI fraud data
    geo_probs = np.column_stack([
        0.10 + (1 - mixed_risk) * 0.20,
        0.60 * np.ones(n),
        0.10 + mixed_risk * 0.20
    ])
    geo_probs = geo_probs / geo_probs.sum(axis=1, keepdims=True)
    behav_df["geographic_risk_score"] = np.array([
        rng.choice([1, 2, 3], p=geo_probs[i]) for i in range(n)
    ]).astype(int)

    behav_df = behav_df.reset_index(drop=True)

    logger.info("Part 3: Merging demographics and behavioral data...")

    assert len(demo_df) == len(behav_df) == N_SAMPLES, f"Length mismatch: demo={len(demo_df)}, behav={len(behav_df)}"
    df_merged = pd.concat([demo_df.reset_index(drop=True), behav_df.reset_index(drop=True)], axis=1)

    null_count = df_merged.isnull().sum().sum()
    assert null_count == 0, f"Merge produced {null_count} null values. Check index alignment."

    df_merged["employment_to_age_ratio"] = (
        df_merged["employment_vintage_days"] /
        ((df_merged["applicant_age_years"] - 18) * 365).clip(lower=1)
    ).clip(0, 1).round(4)

    logger.info("Part 4: Assigning TARGET from INDEPENDENT behavioral + demographic signals...")

    # ── TARGET: TWO INDEPENDENT SIGNALS ──────────────────────────────
    # Behavioral score purely from behavioral features (80% independent)
    behavioral_score = (
        (1 - df_merged["utility_payment_consistency"]) * 0.15
        + df_merged["eod_balance_volatility"]           * 0.12
        + (df_merged["bounced_transaction_count"] / 10) * 0.10
        + df_merged["rent_wallet_share"].clip(0, 1)     * 0.07
        + df_merged["cash_withdrawal_dependency"]        * 0.05
        + (df_merged["min_balance_violation_count"] / 8)* 0.04
        + (1 - df_merged["income_stability_score"])      * 0.06
        + df_merged["cashflow_volatility"]               * 0.05
        + df_merged["gst_to_bank_variance"].clip(0,1)    * 0.04
        + df_merged["customer_concentration_ratio"]      * 0.03
        + df_merged["p2p_circular_loop_flag"]             * 0.04
        + df_merged["turnover_inflation_spike"]           * 0.03
        + df_merged["night_transaction_ratio"]            * 0.04
        + (1 - df_merged["payment_diversity_score"])     * 0.04
        + (1 - df_merged["device_consistency_score"])    * 0.03
        + (df_merged["geographic_risk_score"] - 1) / 2   * 0.02
        + df_merged["revenue_seasonality_index"]         * 0.03
        + (1 - df_merged["essential_vs_lifestyle_ratio"])* 0.06
    )

    # TARGET = 60% behavioral (independent) + 25% demographic + 15% noise
    # The noise prevents either signal from being too predictive alone
    default_score = (
        0.60 * behavioral_score +
        0.25 * demo_risk +
        0.15 * rng.beta(2, 2, N_SAMPLES)  # random noise (more realistic than gaussian)
    )

    threshold = np.percentile(default_score, 75)
    df_merged["TARGET"] = (default_score >= threshold).astype(int)

    actual_rate = df_merged["TARGET"].mean()
    logger.info(f"Default rate: {actual_rate*100:.2f}%")
    assert 0.22 <= actual_rate <= 0.28, f"Default rate {actual_rate:.3f} out of range"

    logger.info("Part 5: Verification checks...")

    behav_cols = [
        "utility_payment_consistency",
        "bounced_transaction_count",
        "eod_balance_volatility",
        "emergency_buffer_months",
        "rent_wallet_share"
    ]
    sep = df_merged.groupby("TARGET")[behav_cols].mean()
    logger.info("\nBehavioral means by TARGET:")
    logger.info("\n" + sep.round(4).to_string())

    for col in behav_cols:
        diff = abs(sep.loc[0, col] - sep.loc[1, col])
        if diff < 0.15:
            logger.warning(f"WEAK SEPARATION: {col} diff={diff:.4f} — increase distribution gap")

    demo_cols = [
        "applicant_age_years",
        "employment_vintage_days",
        "academic_background_tier",
        "owns_property",
        "income_type_risk_score"
    ]
    demo_corr = (df_merged[demo_cols + ["TARGET"]].corr()["TARGET"].drop("TARGET").abs().sort_values(ascending=False))
    logger.info("\nDemographic correlation with TARGET:")
    logger.info("\n" + demo_corr.round(4).to_string())

    high_corr = demo_corr[demo_corr > 0.35]
    if len(high_corr) > 0:
        logger.warning(f"Demographics correlating with TARGET > 0.35 (too strong, risk of leakage):\n{high_corr.to_string()}")
    
    low_corr = demo_corr[demo_corr < 0.03]
    if len(low_corr) > 0:
        logger.warning(f"Demographics with near-zero TARGET correlation (should contribute):\n{low_corr.to_string()}")
    else:
        logger.info("Demographics moderately correlated with TARGET ✅ (all > 0.03, demographics are contributing)")

    behav_corr = (df_merged[behav_cols + ["TARGET"]].corr()["TARGET"].drop("TARGET").abs().sort_values(ascending=False))
    logger.info("\nBehavioral correlation with TARGET:")
    logger.info("\n" + behav_corr.round(4).to_string())

    low_corr = behav_corr[behav_corr < 0.15]
    if len(low_corr) > 0:
        logger.warning(f"Weak behavioral correlation with TARGET:\n{low_corr.to_string()}")
    else:
        logger.info("Behavioral features strongly predict TARGET ✅")

    logger.info(f"\nMerge integrity:\n  Total rows    : {len(df_merged)}\n  Total columns : {len(df_merged.columns)}\n  Null values   : {df_merged.isnull().sum().sum()}\n  Default rate  : {df_merged['TARGET'].mean()*100:.2f}%")
    logger.info("Part 5: Validating and Saving...")
    # All 49 features + TARGET = 50 columns
    # This is the COMPLETE feature set matching feature_engine.py + 5 new UPI features
    expected_cols = [
        # Behavioral (13)
        "utility_payment_consistency", "avg_utility_dpd",
        "rent_wallet_share", "subscription_commitment_ratio",
        "emergency_buffer_months", "eod_balance_volatility",
        "essential_vs_lifestyle_ratio", "cash_withdrawal_dependency",
        "bounced_transaction_count", "telecom_recharge_drop_ratio",
        "min_balance_violation_count",
        "income_stability_score", "income_seasonality_flag",
        # Alternative (3)
        "telecom_number_vintage_days",
        "academic_background_tier", "purpose_of_loan_encoded",
        # Demographic (18)
        "employment_vintage_days", "applicant_age_years",
        "owns_property", "owns_car", "region_risk_tier",
        "address_stability_years", "id_document_age_years",
        "family_burden_ratio", "has_email_flag",
        "income_type_risk_score", "family_status_stability_score",
        "contactability_score", "car_age_years",
        "region_city_risk_score", "address_work_mismatch",
        "employment_to_age_ratio",
        "neighbourhood_default_rate_30", "neighbourhood_default_rate_60",
        # Forensic / MSME (10)
        "p2p_circular_loop_flag", "gst_to_bank_variance",
        "customer_concentration_ratio", "turnover_inflation_spike",
        "identity_device_mismatch", "business_vintage_months",
        "gst_filing_consistency_score", "revenue_seasonality_index",
        "revenue_growth_trend", "cashflow_volatility",
        # NEW UPI-calibrated features (5)
        "night_transaction_ratio", "weekend_spending_ratio",
        "payment_diversity_score", "device_consistency_score",
        "geographic_risk_score",
        # Target
        "TARGET"
    ]
    
    assert len(expected_cols) == 50, f"Expected 50 columns (49 features + TARGET), got {len(expected_cols)}"
    for c in expected_cols:
        assert c in df_merged.columns, f"Missing column {c}"
        
    df_merged = df_merged[expected_cols]
    
    assert sum("EXT_SOURCE" in c for c in df_merged.columns) == 0
    assert df_merged.isnull().sum().sum() == 0
    assert df_merged.shape == (25000, 50)
    
    print(f"Rows generated    : {len(df_merged)}")
    print(f"Columns           : {len(df_merged.columns)}")
    print(f"Default rate      : {df_merged['TARGET'].mean()*100:.2f}%")
    
    corr = df_merged.corr()["TARGET"].sort_values(ascending=False).drop("TARGET")
    print("Top 3 correlations with TARGET:")
    for i, (col, val) in enumerate(corr.head(3).items(), 1):
        print(f"  {i}. {col} ({val:.4f})")
        
    os.makedirs("datasets", exist_ok=True)
    df_merged.to_csv("datasets/ntc_credit_training_v2.csv", index=False)
    logger.info("Saved to datasets/ntc_credit_training_v2.csv")

if __name__ == "__main__":
    build_training_data()

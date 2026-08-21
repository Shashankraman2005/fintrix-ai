import pandas as pd
import numpy as np
import logging
import os
from data_loader import load_raw_data

logger = logging.getLogger(__name__)

def filter_dataset(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Applying dataset filters F1-F5...")
    initial_len = len(df)
    
    # F1: Remove rows where AMT_INCOME_TOTAL > 99th percentile
    p99 = df['AMT_INCOME_TOTAL'].quantile(0.99)
    df = df[df['AMT_INCOME_TOTAL'] <= p99]
    logger.info(f"F1: Removed {initial_len - len(df)} rows where AMT_INCOME_TOTAL > 99th percentile.")
    curr_len = len(df)
    
    # F2: Replace DAYS_EMPLOYED == 365243 with NaN
    mask = df['DAYS_EMPLOYED'] == 365243
    df.loc[mask, 'DAYS_EMPLOYED'] = np.nan
    logger.info(f"F2: Replaced sentinel value 365243 with NaN in DAYS_EMPLOYED for {mask.sum()} rows.")
    
    # F3: Remove rows where OBS_30, AMT_ANNUITY, AMT_GOODS_PRICE are all null
    mask_f3 = df['OBS_30_CNT_SOCIAL_CIRCLE'].isnull() & df['AMT_ANNUITY'].isnull() & df['AMT_GOODS_PRICE'].isnull()
    df = df[~mask_f3]
    logger.info(f"F3: Removed {curr_len - len(df)} rows with zero derivable signal (completely null columns).")
    curr_len = len(df)
    
    # F4: Remove OCCUPATION_TYPE == "Secretaries"
    mask_f4 = df['OCCUPATION_TYPE'] == 'Secretaries'
    df = df[~mask_f4]
    logger.info(f"F4: Removed {curr_len - len(df)} rows where OCCUPATION_TYPE == 'Secretaries'.")
    curr_len = len(df)
    
    # F5: Remove CNT_CHILDREN > 10
    mask_f5 = df['CNT_CHILDREN'] > 10
    df = df[~mask_f5]
    logger.info(f"F5: Removed {curr_len - len(df)} rows where CNT_CHILDREN > 10.")
    
    logger.info(f"Retained {len(df)} rows ({(len(df)/initial_len):.2%} of original).")
    return df

def build_credit_features(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Deriving 14 NTC credit features from behavioral signals...")
    out = pd.DataFrame(index=df.index)
    rng = np.random.default_rng(42)  # Strict reproducibility
    n = len(df)
    
    # Clean division elements
    obs_30 = df['OBS_30_CNT_SOCIAL_CIRCLE'].fillna(1).clip(lower=1)
    obs_60 = df['OBS_60_CNT_SOCIAL_CIRCLE'].fillna(1).clip(lower=1)
    inc = df['AMT_INCOME_TOTAL'].replace(0, np.nan)
    cred = df['AMT_CREDIT'].replace(0, np.nan)
    
    bureau_cols = [
        'AMT_REQ_CREDIT_BUREAU_HOUR', 'AMT_REQ_CREDIT_BUREAU_DAY',
        'AMT_REQ_CREDIT_BUREAU_WEEK', 'AMT_REQ_CREDIT_BUREAU_MON',
        'AMT_REQ_CREDIT_BUREAU_QRT', 'AMT_REQ_CREDIT_BUREAU_YEAR'
    ]
    inq_df = df[bureau_cols].fillna(0)
    inq_short = inq_df['AMT_REQ_CREDIT_BUREAU_HOUR'] + inq_df['AMT_REQ_CREDIT_BUREAU_DAY'] + inq_df['AMT_REQ_CREDIT_BUREAU_WEEK']
    inq_total = inq_df.sum(axis=1).replace(0, np.nan)
    
    # 1. utility_payment_consistency
    out['utility_payment_consistency'] = 1 - (df['DEF_30_CNT_SOCIAL_CIRCLE'].fillna(0) / obs_30)
    
    # 2. avg_utility_dpd
    out['avg_utility_dpd'] = (df['DEF_30_CNT_SOCIAL_CIRCLE'].fillna(0) / obs_30) * 30.0
    
    # 3. rent_wallet_share
    out['rent_wallet_share'] = df['AMT_ANNUITY'] / inc
    
    # 4. subscription_commitment_ratio
    out['subscription_commitment_ratio'] = out['rent_wallet_share'] * 0.3
    
    # 5. emergency_buffer_months
    out['emergency_buffer_months'] = (inc / 12) / (cred / 60)
    
    # 6. eod_balance_volatility
    out['eod_balance_volatility'] = (df['DEF_60_CNT_SOCIAL_CIRCLE'].fillna(0) / obs_60) * 0.5 + (inq_short / inq_total.fillna(1)) * 0.5
    
    # 7. essential_vs_lifestyle_ratio
    out["essential_vs_lifestyle_ratio"] = (
        df['AMT_GOODS_PRICE'] / cred.fillna(df['AMT_GOODS_PRICE'])
    ).clip(0, 1).fillna(0.85).round(4)
    
    # 8. cash_withdrawal_dependency
    out['cash_withdrawal_dependency'] = inq_short / inq_total.fillna(1)
    
    # 9. bounced_transaction_count
    # Fill nulls with 0 so astype(int) works properly without losing rows
    bounces = df['DEF_60_CNT_SOCIAL_CIRCLE'].fillna(0) * 0.5 + (inq_df['AMT_REQ_CREDIT_BUREAU_HOUR'] + inq_df['AMT_REQ_CREDIT_BUREAU_DAY']) * 0.3
    out['bounced_transaction_count'] = bounces.fillna(0).round().astype(int)
    
    # 10. telecom_number_vintage_days
    out['telecom_number_vintage_days'] = -df['DAYS_LAST_PHONE_CHANGE']
    
    # 11. academic_background_tier
    edu_map = {
        "Academic degree"               : 5,
        "Higher education"              : 4,
        "Incomplete higher"             : 3,
        "Secondary / secondary special" : 2,
        "Lower secondary"               : 1,
    }
    out["academic_background_tier"] = (
        df["NAME_EDUCATION_TYPE"].map(edu_map).fillna(2).astype(int)
    )
    
    # 12. purpose_of_loan_encoded
    contract_map = {'Cash loans': 1, 'Revolving loans': 2}
    out['purpose_of_loan_encoded'] = df['NAME_CONTRACT_TYPE'].map(contract_map).fillna(1)
    
    # 13. employment_vintage_days
    out['employment_vintage_days'] = -df['DAYS_EMPLOYED']
    
    # 14. telecom_recharge_drop_ratio (Noisy Proxy 1)
    t1 = (-df['DAYS_LAST_PHONE_CHANGE'].fillna(0) / 365).clip(lower=0, upper=1) * 0.6
    t2 = (inq_df['AMT_REQ_CREDIT_BUREAU_MON'] / 3).clip(lower=0, upper=1) * 0.4
    noise_term_1 = rng.normal(0, 0.08, n)
    out['telecom_recharge_drop_ratio'] = (t1 + t2 + noise_term_1).clip(lower=0, upper=1)
    
    # 15. min_balance_violation_count (Noisy Proxy 2)
    noise_term_2 = rng.normal(0, 0.5, n)
    v_count = inq_df['AMT_REQ_CREDIT_BUREAU_HOUR'] * 2 + inq_df['AMT_REQ_CREDIT_BUREAU_DAY'] + noise_term_2
    out['min_balance_violation_count'] = v_count.clip(lower=0, upper=8).round().astype(int)
    
    # =========================================================================
    # BLOCK C — 8 Individual-Level Direct Features
    # =========================================================================

    # 16. applicant_age_years
    # Source: -DAYS_BIRTH / 365
    # Logic: Younger applicants default more. Direct individual signal.
    # Range: [18, 70]
    out["applicant_age_years"] = (
        -df["DAYS_BIRTH"] / 365
    ).clip(18, 70).round(1)

    # 17. owns_property
    # Source: FLAG_OWN_REALTY
    # Logic: Property ownership = asset stability = lower default risk.
    # Range: {0, 1}
    out["owns_property"] = (
        df["FLAG_OWN_REALTY"].map({"Y": 1, "N": 0}).fillna(0).astype(int)
    )

    # 18. owns_car
    # Source: FLAG_OWN_CAR
    # Logic: Vehicle ownership = asset proxy.
    # Range: {0, 1}
    out["owns_car"] = (
        df["FLAG_OWN_CAR"].map({"Y": 1, "N": 0}).fillna(0).astype(int)
    )

    # 19. region_risk_tier
    # Source: REGION_RATING_CLIENT
    # Logic: 1=low risk region, 2=medium, 3=high risk region.
    # Range: {1, 2, 3}
    out["region_risk_tier"] = (
        df["REGION_RATING_CLIENT"].fillna(2).astype(int)
    )

    # 20. address_stability_years
    # Source: -DAYS_REGISTRATION / 365
    # Logic: Longer at same address = more stable = lower default risk.
    # Range: [0, 30]
    out["address_stability_years"] = (
        -df["DAYS_REGISTRATION"].fillna(-365) / 365
    ).clip(0, 30).round(1)

    # 21. id_document_age_years
    # Source: -DAYS_ID_PUBLISH / 365
    # Logic: Very recently published ID = mild fraud/instability signal.
    # Range: [0, 20]
    out["id_document_age_years"] = (
        -df["DAYS_ID_PUBLISH"].fillna(-365) / 365
    ).clip(0, 20).round(1)

    # 22. family_burden_ratio
    # Source: CNT_CHILDREN / CNT_FAM_MEMBERS
    # Logic: High ratio of children to family = higher financial burden.
    # Range: [0, 1]
    fam = df["CNT_FAM_MEMBERS"].replace(0, np.nan).fillna(1)
    out["family_burden_ratio"] = (
        df["CNT_CHILDREN"].fillna(0) / fam
    ).clip(0, 1).round(4)

    # 23. has_email_flag
    # Source: FLAG_EMAIL
    # Logic: Email = digital footprint = more traceable = lower risk.
    # Range: {0, 1}
    out["has_email_flag"] = df["FLAG_EMAIL"].fillna(0).astype(int)

    # =========================================================================
    # BLOCK D — 7 Income, Employment and Stability Features
    # =========================================================================

    # 24. income_type_risk_score
    # Source: NAME_INCOME_TYPE ordinal risk encoding
    # Logic: Employment type is the strongest individual default predictor.
    #        Unemployed and maternity leave = highest risk.
    #        Working and commercial associate = lowest risk.
    # Range: [1, 5] integer — higher = higher risk
    income_type_risk_map = {
        "Working"                : 1,
        "Commercial associate"   : 1,
        "Pensioner"              : 2,
        "State servant"          : 2,
        "Student"                : 3,
        "Businessman"            : 3,
        "Maternity leave"        : 4,
        "Unemployed"             : 5,
    }
    out["income_type_risk_score"] = (
        df["NAME_INCOME_TYPE"]
        .map(income_type_risk_map)
        .fillna(3)
        .astype(int)
    )

    # 25. family_status_stability_score
    # Source: NAME_FAMILY_STATUS ordinal encoding
    # Logic: Married applicants statistically default less.
    #        Single and separated have higher default rates.
    # Range: [1, 4] integer — higher = less stable
    family_status_map = {
        "Married"           : 1,
        "Civil marriage"    : 2,
        "Widow"             : 2,
        "Separated"         : 3,
        "Single / not married": 4,
    }
    out["family_status_stability_score"] = (
        df["NAME_FAMILY_STATUS"]
        .map(family_status_map)
        .fillna(2)
        .astype(int)
    )

    # 26. contactability_score
    # Source: FLAG_WORK_PHONE + FLAG_EMP_PHONE + FLAG_PHONE + FLAG_EMAIL
    # Logic: More contact points = more traceable = lower default risk.
    #        Untraceable borrowers default and disappear.
    # Range: [0, 4] integer
    out["contactability_score"] = (
        df["FLAG_WORK_PHONE"].fillna(0) +
        df["FLAG_EMP_PHONE"].fillna(0) +
        df["FLAG_PHONE"].fillna(0) +
        df["FLAG_EMAIL"].fillna(0)
    ).clip(0, 4).astype(int)

    # 27. car_age_years
    # Source: OWN_CAR_AGE
    # Logic: Owning a newer car = higher wealth stability.
    #        NaN means no car — fill with 99 as "no car" signal.
    #        High values (old car) = modest means.
    # Range: [0, 99]
    out["car_age_years"] = (
        df["OWN_CAR_AGE"].fillna(99).clip(0, 99).round(0).astype(int)
    )

    # 28. region_city_risk_score
    # Source: REGION_RATING_CLIENT_W_CITY
    # Logic: More granular than region_risk_tier —
    #        includes city-level risk adjustment.
    # Range: {1, 2, 3}
    out["region_city_risk_score"] = (
        df["REGION_RATING_CLIENT_W_CITY"].fillna(2).astype(int)
    )

    # 29. address_work_mismatch
    # Source: LIVE_CITY_NOT_WORK_CITY + REG_CITY_NOT_LIVE_CITY
    # Logic: Living in a different city from registered address or
    #        workplace = instability signal = higher default risk.
    # Range: [0, 2] integer
    out["address_work_mismatch"] = (
        df["LIVE_CITY_NOT_WORK_CITY"].fillna(0) +
        df["REG_CITY_NOT_LIVE_CITY"].fillna(0)
    ).clip(0, 2).astype(int)

    # 30. employment_to_age_ratio
    # Source: employment_vintage_days / (applicant_age_years × 365)
    # Logic: What fraction of adult life has this person been employed.
    #        Low ratio despite older age = chronic unemployment = high risk.
    # Range: [0, 1]
    working_life_days = (
        (out["applicant_age_years"] - 18) * 365
    ).clip(lower=1)
    out["employment_to_age_ratio"] = (
        out["employment_vintage_days"] / working_life_days
    ).clip(0, 1).round(4)

    # =====================================================
    # BLOCK E — 3 Interaction Features
    # =====================================================

    # 31. stress_composite_score
    # Include TARGET
    out['TARGET'] = df['TARGET'].astype(int)
    
    return out

def _validate(df: pd.DataFrame) -> None:
    logger.info("Executing Hard Validation Guardrails...")
    
    expected_cols = [
        "utility_payment_consistency",
        "avg_utility_dpd",
        "rent_wallet_share",
        "subscription_commitment_ratio",
        "emergency_buffer_months",
        "eod_balance_volatility",
        "essential_vs_lifestyle_ratio",
        "cash_withdrawal_dependency",
        "bounced_transaction_count",
        "telecom_number_vintage_days",
        "academic_background_tier",
        "purpose_of_loan_encoded",
        "employment_vintage_days",
        "telecom_recharge_drop_ratio",
        "min_balance_violation_count",
        "applicant_age_years",
        "owns_property",
        "owns_car",
        "region_risk_tier",
        "address_stability_years",
        "id_document_age_years",
        "family_burden_ratio",
        "has_email_flag",
        "income_type_risk_score",
        "family_status_stability_score",
        "contactability_score",
        "car_age_years",
        "region_city_risk_score",
        "address_work_mismatch",
        "employment_to_age_ratio",
        "TARGET"
    ]
    
    # 1. Column names check
    missing = set(expected_cols) - set(df.columns)
    if missing:
        raise ValueError(f"CRITICAL: Missing expected columns: {missing}")
        
    # 2. Hard guard against EXT_SOURCE
    if any('EXT_SOURCE' in col for col in df.columns):
        raise ValueError("Bureau data must never enter this model")
        
    # 3. Null rate
    for col in df.columns:
        null_pct = df[col].isnull().mean()
        if null_pct > 0.05:
            logger.warning(f"Validation Warning: Null rate for {col} is {null_pct:.2%}, which exceeds the 5% warning threshold.")
            
    # 4. Range [0,1] for ratio features (allowing slight float imprecision)
    ratios = ['utility_payment_consistency', 'rent_wallet_share', 
              'subscription_commitment_ratio', 'eod_balance_volatility',
              'essential_vs_lifestyle_ratio', 'cash_withdrawal_dependency',
              'telecom_recharge_drop_ratio', 'family_burden_ratio', 'employment_to_age_ratio']
    for col in ratios:
        if df[col].min() < -0.01 or df[col].max() > 1.01:
            logger.warning(f"Ratio Alert: {col} is out of expected [0,1] bounds. Min: {df[col].min():.3f}, Max: {df[col].max():.3f}")
            
    # 5. Non-negative counts/days
    non_neg = ['avg_utility_dpd', 'emergency_buffer_months', 'bounced_transaction_count',
               'min_balance_violation_count', 'applicant_age_years',
               'address_stability_years', 'id_document_age_years', 'region_risk_tier',
               'contactability_score', 'car_age_years', 'address_work_mismatch',
               'income_type_risk_score', 'family_status_stability_score', 'region_city_risk_score']
    if df['telecom_number_vintage_days'].min() < 0:
        logger.warning(f"telecom_number_vintage_days has negative values: {df['telecom_number_vintage_days'].min()}")
    if df['employment_vintage_days'].min() < 0:
        logger.warning(f"employment_vintage_days has negative values: {df['employment_vintage_days'].min()}")
        
    for col in non_neg:
        if df[col].min() < 0:
            logger.warning(f"Count/Day constraint failed: {col} contains negative values (Min = {df[col].min()})")
            
    # 6. Default rate bounds
    default_rate = df['TARGET'].mean()
    if not (0.05 <= default_rate <= 0.40):
        logger.warning(f"Overall Dataset Risk Warning: Default rate {default_rate:.2%} is outside [5%, 40%].")
        
    logger.info("Validation complete. All blocking constraints passed.")

def save(df: pd.DataFrame, path: str) -> None:
    logger.info(f"Writing fully transformed training dataset to {path}...")
    df.to_csv(path, index=False)
    
def print_distribution_report(df: pd.DataFrame) -> None:
    print("\n" + "═"*80)
    print(" 📊 FEATURE DISTRIBUTION REPORT")
    print("═"*80)
    stats = df.describe().T[['mean', 'std', 'min', 'max']]
    print(stats.to_string(float_format=lambda x: f"{x:.4f}"))
    
    print("\n" + "═"*80)
    print(" 🎯 CORRELATION WITH TARGET")
    print("═"*80)
    corr = df.corr()['TARGET'].drop('TARGET').sort_values(ascending=False)
    for feat, val in corr.items():
        bar_len = min(int(abs(val) * 100), 30)
        bar = ("█" * bar_len) if val > 0 else ("▒" * bar_len)
        print(f"{feat:<35} | {val:>7.4f} | {bar}")
    print("═"*80 + "\n")

if __name__ == "__main__":
    # Configure logging specifically for direct execution
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    
    # Execute pipeline
    raw_frame = load_raw_data()
    filtered_frame = filter_dataset(raw_frame)
    final_features = build_credit_features(filtered_frame)
    _validate(final_features)
    
    os.makedirs('datasets', exist_ok=True)
    save(final_features, 'datasets/ntc_credit_training.csv')
    print_distribution_report(final_features)

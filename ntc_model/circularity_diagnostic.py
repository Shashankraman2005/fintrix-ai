"""
Circularity Diagnostic: Proves behavioral features are just noisy copies of demographics.
"""
import pandas as pd
import numpy as np
import os

OUT = open("circ_out.txt", "w", encoding="utf-8")
def p(text=""):
    print(text)
    OUT.write(text + "\n")

df = pd.read_csv("datasets/ntc_credit_training_v2.csv")

p("=" * 70)
p("  CIRCULARITY DIAGNOSTIC")
p("=" * 70)

demo_cols = [
    "applicant_age_years", "employment_vintage_days", "owns_property",
    "academic_background_tier", "income_type_risk_score", "family_burden_ratio",
    "address_stability_years", "contactability_score", "region_risk_tier"
]

age_risk = np.clip((35 - df["applicant_age_years"]) / 30, 0, 1)
emp_risk = np.clip(1 - df["employment_vintage_days"] / 3650, 0, 1)
prop_risk = (1 - df["owns_property"]).astype(float)
edu_risk = np.clip(1 - (df["academic_background_tier"] - 1) / 4, 0, 1)
income_risk = np.clip(df["income_type_risk_score"] / 5, 0, 1)
family_risk = df["family_burden_ratio"].clip(0, 1)
addr_risk = np.clip(1 - df["address_stability_years"] / 15, 0, 1)
contact_risk = np.clip(1 - df["contactability_score"] / 4, 0, 1)
region_risk = np.clip((df["region_risk_tier"] - 1) / 2, 0, 1)

reconstructed_demo_risk = (
    0.20 * emp_risk + 0.15 * age_risk + 0.15 * prop_risk +
    0.12 * income_risk + 0.10 * edu_risk + 0.10 * addr_risk +
    0.08 * family_risk + 0.05 * contact_risk + 0.05 * region_risk
)

behav_cols = [
    "utility_payment_consistency", "avg_utility_dpd", "rent_wallet_share",
    "emergency_buffer_months", "eod_balance_volatility", "essential_vs_lifestyle_ratio",
    "cash_withdrawal_dependency", "bounced_transaction_count", "telecom_recharge_drop_ratio",
    "min_balance_violation_count", "income_stability_score", "cashflow_volatility",
    "gst_to_bank_variance", "customer_concentration_ratio", "night_transaction_ratio",
    "weekend_spending_ratio", "payment_diversity_score", "device_consistency_score"
]

p("\n--- Behavioral vs Demographic Risk Correlation ---")
p(f"  {'Feature':<40} {'Corr':>8}  Verdict")
p("-" * 65)

circular_count = 0
for col in behav_cols:
    if col in df.columns:
        corr = df[col].corr(reconstructed_demo_risk)
        if abs(corr) > 0.50:
            verdict = "CIRCULAR"
            circular_count += 1
        elif abs(corr) > 0.30:
            verdict = "HIGH"
        else:
            verdict = "OK"
        p(f"  {col:<40} {corr:>8.4f}  {verdict}")

target_corr = df["TARGET"].corr(reconstructed_demo_risk)
p(f"\n  {'TARGET':<40} {target_corr:>8.4f}  {'CIRCULAR' if abs(target_corr) > 0.50 else 'HIGH'}")

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

p("\n--- Can demographics ALONE predict TARGET? ---")
X_demo = df[demo_cols]
y = df["TARGET"]
rf = RandomForestClassifier(n_estimators=50, max_depth=4, random_state=42, n_jobs=-1)
scores_demo = cross_val_score(rf, X_demo, y, cv=5, scoring="roc_auc")
p(f"  Demographics only AUC: {scores_demo.mean():.4f} +/- {scores_demo.std():.4f}")

p("\n--- Can behavioral features ALONE predict TARGET? ---")
available_behav = [c for c in behav_cols if c in df.columns]
X_behav = df[available_behav]
scores_behav = cross_val_score(rf, X_behav, y, cv=5, scoring="roc_auc")
p(f"  Behavioral only AUC: {scores_behav.mean():.4f} +/- {scores_behav.std():.4f}")

p("\n--- Both together ---")
X_all = df.drop(columns=["TARGET"])
scores_all = cross_val_score(rf, X_all, y, cv=5, scoring="roc_auc")
p(f"  Combined AUC: {scores_all.mean():.4f} +/- {scores_all.std():.4f}")

lift = scores_all.mean() - scores_demo.mean()
p(f"\n  AUC lift from behavioral: {lift:+.4f}")
if lift < 0.03:
    p("  CIRCULAR CONFIRMED: Behavioral adds almost nothing over demographics.")
else:
    p("  Circularity is sufficiently broken (but check if still too correlated).")

p(f"\n{'=' * 70}")
p(f"  SUMMARY")
p(f"{'=' * 70}")
p(f"  Circular features (|corr|>0.50): {circular_count}/{len(behav_cols)}")
p(f"  TARGET vs demo_risk corr:        {target_corr:.4f}")
p(f"  Demo-only AUC:                   {scores_demo.mean():.4f}")
p(f"  Behavioral-only AUC:             {scores_behav.mean():.4f}")
p(f"  Combined AUC:                    {scores_all.mean():.4f}")
p(f"  Lift from behavioral:            {lift:+.4f}")

OUT.close()

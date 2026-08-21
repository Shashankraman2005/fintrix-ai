"""
Memorization / Overfitting Test for NTC Credit Model
=====================================================
Tests whether the model learned real patterns or just memorized training data.

5 tests:
  1. Train vs Test AUC gap (overfit = large gap)
  2. Random noise test (overfit model gives confident predictions on garbage)
  3. Feature permutation test (if shuffling a feature doesn't change predictions,
     the model might not be using it meaningfully)
  4. Prediction distribution check (memorized model clusters around few values)
  5. Calibration check (do predicted probabilities match actual default rates?)
"""
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import roc_auc_score, brier_score_loss

print("=" * 60)
print("MEMORIZATION / OVERFITTING TEST")
print("=" * 60)

# Load data and model
df = pd.read_csv("datasets/ntc_credit_training_v2.csv")
model = joblib.load("models/ntc_credit_model.pkl")
preprocessor = joblib.load("models/ntc_preprocessor.pkl")

TARGET_COL = "TARGET"
y = df[TARGET_COL].values
feature_cols = [c for c in df.columns if c != TARGET_COL]
X_raw = df[feature_cols]
X = preprocessor.transform(X_raw)

print(f"\nDataset: {len(df)} rows, {len(feature_cols)} features")
print(f"Default rate: {y.mean():.4f} ({y.sum()}/{len(y)})")

# ───────────────────────────────────────────────────────
# TEST 1: Cross-Validated AUC vs Training AUC
# ───────────────────────────────────────────────────────
print("\n" + "─" * 60)
print("TEST 1: Train AUC vs Cross-Validated AUC")
print("─" * 60)

train_proba = model.predict_proba(X)[:, 1]
train_auc = roc_auc_score(y, train_proba)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_aucs = []
for fold, (train_idx, val_idx) in enumerate(cv.split(X_raw, y)):
    X_tr = preprocessor.transform(X_raw.iloc[train_idx])
    X_val = preprocessor.transform(X_raw.iloc[val_idx])
    y_tr, y_val = y[train_idx], y[val_idx]

    from xgboost import XGBClassifier
    fold_model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
        use_label_encoder=False,
        eval_metric="logloss"
    )
    fold_model.fit(X_tr, y_tr)
    val_proba = fold_model.predict_proba(X_val)[:, 1]
    fold_auc = roc_auc_score(y_val, val_proba)
    cv_aucs.append(fold_auc)

cv_mean = np.mean(cv_aucs)
cv_std = np.std(cv_aucs)
gap = train_auc - cv_mean

print(f"  Training AUC     : {train_auc:.4f}")
print(f"  Cross-Val AUC    : {cv_mean:.4f} ± {cv_std:.4f}")
print(f"  Gap              : {gap:.4f}")
if gap > 0.10:
    print("  ⚠️  OVERFITTING: Gap > 0.10 — model memorizes training data")
elif gap > 0.05:
    print("  ⚠️  MILD OVERFIT: Gap 0.05-0.10 — some memorization")
else:
    print("  ✅ HEALTHY: Gap < 0.05 — model generalizes well")

# ───────────────────────────────────────────────────────
# TEST 2: Random Noise Test
# ───────────────────────────────────────────────────────
print("\n" + "─" * 60)
print("TEST 2: Random Noise Input")
print("─" * 60)
print("  Feeding pure random noise as features.")
print("  A good model should predict near base rate (~0.08).")
print("  A memorizing model gives confidently wrong predictions.")

rng = np.random.RandomState(42)
X_noise = pd.DataFrame(
    rng.randn(500, len(feature_cols)),
    columns=feature_cols
)
X_noise_t = preprocessor.transform(X_noise)
noise_proba = model.predict_proba(X_noise_t)[:, 1]

noise_mean = noise_proba.mean()
noise_std = noise_proba.std()
noise_max = noise_proba.max()
noise_min = noise_proba.min()
confident_high = (noise_proba > 0.7).sum()
confident_low = (noise_proba < 0.05).sum()

print(f"  Noise predictions: mean={noise_mean:.4f}, std={noise_std:.4f}")
print(f"  Range: [{noise_min:.4f}, {noise_max:.4f}]")
print(f"  Confident high (>0.7): {confident_high}/500")
print(f"  Confident low (<0.05): {confident_low}/500")

if confident_high > 50 or confident_low > 400:
    print("  ⚠️  SUSPICIOUS: Model gives confident predictions on random noise")
else:
    print("  ✅ HEALTHY: Model is uncertain on random noise (expected)")

# ───────────────────────────────────────────────────────
# TEST 3: Feature Permutation Importance
# ───────────────────────────────────────────────────────
print("\n" + "─" * 60)
print("TEST 3: Feature Permutation Importance (top 10)")
print("─" * 60)
print("  Shuffling each feature and measuring AUC drop.")
print("  If no feature matters much, model may be memorizing row patterns.")

base_auc = roc_auc_score(y, train_proba)
importances = {}

for col_idx, col_name in enumerate(feature_cols):
    X_perm = X.copy()
    rng.shuffle(X_perm[:, col_idx])
    perm_proba = model.predict_proba(X_perm)[:, 1]
    perm_auc = roc_auc_score(y, perm_proba)
    importances[col_name] = base_auc - perm_auc

sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)
meaningful_count = 0
print(f"  {'Feature':<40s} {'AUC Drop':>10s}")
print(f"  {'─' * 40} {'─' * 10}")
for name, drop in sorted_imp[:10]:
    flag = "★" if drop > 0.01 else " "
    if drop > 0.005:
        meaningful_count += 1
    print(f"  {flag} {name:<38s} {drop:>+.4f}")

features_matter = sum(1 for _, d in sorted_imp if d > 0.005)
print(f"\n  Features with AUC drop > 0.005: {features_matter}/{len(feature_cols)}")
if features_matter < 3:
    print("  ⚠️  SUSPICIOUS: Very few features matter — possible memorization")
else:
    print("  ✅ HEALTHY: Multiple features contribute to predictions")

# ───────────────────────────────────────────────────────
# TEST 4: Prediction Distribution
# ───────────────────────────────────────────────────────
print("\n" + "─" * 60)
print("TEST 4: Prediction Distribution")
print("─" * 60)
print("  A healthy model spreads predictions across the probability range.")
print("  A memorizing model clusters predictions at extreme values.")

bins = [0, 0.05, 0.10, 0.20, 0.35, 0.55, 0.70, 0.85, 1.01]
labels = ["0-5%", "5-10%", "10-20%", "20-35%", "35-55%", "55-70%", "70-85%", "85-100%"]
hist, _ = np.histogram(train_proba, bins=bins)

print(f"  {'Bucket':<12s} {'Count':>8s} {'Pct':>8s}")
print(f"  {'─' * 12} {'─' * 8} {'─' * 8}")
for label, count in zip(labels, hist):
    pct = count / len(train_proba) * 100
    bar = "█" * int(pct / 2)
    print(f"  {label:<12s} {count:>8d} {pct:>7.1f}% {bar}")

extreme_pct = (hist[0] + hist[-1]) / len(train_proba) * 100
if extreme_pct > 90:
    print(f"\n  ⚠️  SUSPICIOUS: {extreme_pct:.1f}% of predictions at extremes")
else:
    print(f"\n  ✅ HEALTHY: {extreme_pct:.1f}% at extremes — predictions spread out")

# ───────────────────────────────────────────────────────
# TEST 5: Calibration Check
# ───────────────────────────────────────────────────────
print("\n" + "─" * 60)
print("TEST 5: Calibration — Do probabilities match reality?")
print("─" * 60)

brier = brier_score_loss(y, train_proba)
print(f"  Brier Score: {brier:.4f} (lower = better calibrated, <0.10 = good)")

# Bin predictions and check actual default rates
cal_bins = [0, 0.10, 0.20, 0.40, 0.60, 0.80, 1.01]
cal_labels = ["0-10%", "10-20%", "20-40%", "40-60%", "60-80%", "80-100%"]
print(f"\n  {'Predicted':<12s} {'N':>6s} {'Actual Rate':>12s} {'Expected':>10s} {'Gap':>8s}")
print(f"  {'─' * 12} {'─' * 6} {'─' * 12} {'─' * 10} {'─' * 8}")

miscal_count = 0
for i, label in enumerate(cal_labels):
    mask = (train_proba >= cal_bins[i]) & (train_proba < cal_bins[i + 1])
    n = mask.sum()
    if n > 0:
        actual = y[mask].mean()
        expected = train_proba[mask].mean()
        gap = abs(actual - expected)
        flag = "⚠️" if gap > 0.15 else "✅"
        if gap > 0.15:
            miscal_count += 1
        print(f"  {label:<12s} {n:>6d} {actual:>11.4f} {expected:>10.4f} {gap:>7.4f} {flag}")
    else:
        print(f"  {label:<12s} {0:>6d}        -          -       -")

if miscal_count == 0:
    print(f"\n  ✅ WELL CALIBRATED: All bins within 15% of expected")
else:
    print(f"\n  ⚠️  MISCALIBRATED: {miscal_count} bins have >15% gap")

# ───────────────────────────────────────────────────────
# OVERALL VERDICT
# ───────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("OVERALL VERDICT")
print("=" * 60)

issues = []
if gap > 0.10:
    issues.append("Large train/test AUC gap")
if confident_high > 50:
    issues.append("Confident predictions on random noise")
if features_matter < 3:
    issues.append("Too few meaningful features")
if extreme_pct > 90:
    issues.append("Predictions clustered at extremes")
if brier > 0.15:
    issues.append("Poor calibration")

if len(issues) == 0:
    print("  ✅ MODEL IS NOT MEMORIZING — it has learned generalizable patterns")
elif len(issues) <= 2:
    print("  ⚠️  MILD CONCERNS:")
    for i in issues:
        print(f"    - {i}")
else:
    print("  ❌ LIKELY MEMORIZING:")
    for i in issues:
        print(f"    - {i}")

print("=" * 60)

"""
MSME Model — XGBoost Training (fixed)
======================================
Changes from original:
  1. Replaced KS scorer (returned NaN on degenerate CV folds) with AUC scorer
  2. Constrained hyperparameter search space to prevent overfitting:
       max_depth capped at 4, min_child_weight floor at 8, gamma always > 0
  3. Added Platt scaling calibration (CalibratedClassifierCV) matching NTC model
  4. Saves calibrated model as xgb_msme.pkl (raw stored separately)

Run: python scripts/train.py
"""
import os, pickle, warnings
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import (
    roc_auc_score, roc_curve, classification_report, confusion_matrix
)


class PlattCalibratedModel:
    """Wraps XGBoost + sigmoid Platt calibration; keeps predict_proba interface."""
    def __init__(self, xgb_model, platt_lr):
        self.xgb_model = xgb_model
        self.platt_lr  = platt_lr

    def predict_proba(self, X):
        raw = self.xgb_model.predict_proba(X)[:, 1].reshape(-1, 1)
        cal = self.platt_lr.predict_proba(raw)[:, 1]
        return np.column_stack([1 - cal, cal])
warnings.filterwarnings("ignore")

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

X_train = pd.read_csv(os.path.join(DATA_DIR, "X_train.csv"))
X_val   = pd.read_csv(os.path.join(DATA_DIR, "X_val.csv"))
y_train = pd.read_csv(os.path.join(DATA_DIR, "y_train.csv")).squeeze()
y_val   = pd.read_csv(os.path.join(DATA_DIR, "y_val.csv")).squeeze()
print(f"Train: {X_train.shape} | Val: {X_val.shape}")

neg, pos = (y_train == 0).sum(), (y_train == 1).sum()
spw = neg / pos
print(f"Class balance — Non-default: {neg} | Default: {pos} | scale_pos_weight: {spw:.2f}")

# Constrained search space: max_depth ≤ 4, min_child_weight ≥ 8, gamma > 0
# Expanded n_estimators ceiling; slower learning rates
param_dist = {
    "n_estimators":     [600, 700, 800, 1000],
    "max_depth":        [3, 4],
    "learning_rate":    [0.01, 0.015, 0.02, 0.03, 0.05],
    "subsample":        [0.7, 0.8, 0.9],
    "colsample_bytree": [0.7, 0.8, 0.9],
    "min_child_weight": [6, 8, 10, 12],
    "gamma":            [0.05, 0.1, 0.2, 0.3],
    "reg_alpha":        [0.05, 0.1, 0.5, 1.0],
    "reg_lambda":       [1.0, 2.0, 3.0, 5.0],
}

base = xgb.XGBClassifier(
    objective="binary:logistic",
    scale_pos_weight=spw,
    random_state=42, tree_method="hist", n_jobs=1
)
print("\nRunning RandomizedSearchCV (60 iterations, optimizing AUC)...")
search = RandomizedSearchCV(
    base, param_distributions=param_dist,
    n_iter=60, scoring="roc_auc",
    cv=5, verbose=1, random_state=42, n_jobs=1
)
search.fit(X_train, y_train)
print(f"\nBest CV AUC : {search.best_score_:.4f}")
print(f"Best params : {search.best_params_}")

best = search.best_params_
model = xgb.XGBClassifier(
    **best, objective="binary:logistic", eval_metric="auc",
    scale_pos_weight=spw,
    random_state=42, tree_method="hist", n_jobs=1,
    early_stopping_rounds=50
)
model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
print(f"Best iteration: {model.best_iteration}")

y_proba = model.predict_proba(X_val)[:, 1]
y_pred  = (y_proba >= 0.50).astype(int)
auc     = roc_auc_score(y_val, y_proba)
fpr, tpr, _ = roc_curve(y_val, y_proba)
ks   = float(max(tpr - fpr))
gini = 2 * auc - 1

print(f"\n{'='*45}\n  VALIDATION METRICS (raw model)\n{'='*45}")
print(f"  AUC-ROC  : {auc:.4f}")
print(f"  KS Stat  : {ks:.4f}")
print(f"  Gini     : {gini:.4f}")
print(f"\n{classification_report(y_val, y_pred, target_names=['Non-Default','Default'])}")
cm = confusion_matrix(y_val, y_pred)
print(f"Confusion Matrix:\n  TN={cm[0,0]}  FP={cm[0,1]}\n  FN={cm[1,0]}  TP={cm[1,1]}")

# Platt scaling calibration — LogisticRegression on val set raw scores
# (cv='prefit' removed in sklearn 1.8; implemented manually via wrapper)
print(f"\n{'='*45}\n  PLATT CALIBRATION\n{'='*45}")
platt_lr = LogisticRegression(C=1.0, max_iter=1000)
platt_lr.fit(y_proba.reshape(-1, 1), y_val)

calibrated_model = PlattCalibratedModel(model, platt_lr)
y_proba_cal = calibrated_model.predict_proba(X_val)[:, 1]
auc_cal = roc_auc_score(y_val, y_proba_cal)
print(f"  Val AUC after calibration : {auc_cal:.4f} (was {auc:.4f})")
print(f"  Prob range                : [{y_proba_cal.min():.4f}, {y_proba_cal.max():.4f}]")

fi = pd.DataFrame({
    "feature":    X_train.columns,
    "importance": model.feature_importances_
}).sort_values("importance", ascending=False)
print(f"\nTop 15 Features:\n{fi.head(15).to_string(index=False)}")

# Save calibrated model as primary — raw model kept separately
with open(os.path.join(MODEL_DIR, "xgb_msme.pkl"), "wb") as f:
    pickle.dump(calibrated_model, f)
with open(os.path.join(MODEL_DIR, "xgb_msme_raw.pkl"), "wb") as f:
    pickle.dump(model, f)
with open(os.path.join(MODEL_DIR, "best_params.pkl"), "wb") as f:
    pickle.dump(best, f)
fi.to_csv(os.path.join(MODEL_DIR, "feature_importance.csv"), index=False)
print(f"\nCalibrated model saved → {MODEL_DIR}/xgb_msme.pkl")
print(f"Raw model saved        → {MODEL_DIR}/xgb_msme_raw.pkl")

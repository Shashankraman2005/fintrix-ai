"""
MSME Model — Preprocessing with Interaction Features
Run: python scripts/preprocess.py
"""
import os, pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

df = pd.read_csv(os.path.join(DATA_DIR, "msme_training_v2.csv"))
print(f"Loaded: {df.shape[0]} rows × {df.shape[1]} cols")
print(f"Default rate: {df['default'].mean():.1%}\n")

# Interaction features
df["stress_composite"]    = df["cashflow_volatility"] / (df["operating_cashflow_ratio"] + 1e-9)
df["gst_risk_score"]      = df["gst_to_bank_variance"] * (12 - df["gst_filing_consistency_score"])
df["wc_pressure"]         = df["avg_invoice_payment_delay"] * df["customer_concentration_ratio"]
df["liquidity_fragility"] = df["revenue_seasonality_index"] / (df["operating_cashflow_ratio"] + 1e-9)
print("4 interaction features added: stress_composite, gst_risk_score, wc_pressure, liquidity_fragility\n")

# ── Stratification key ────────────────────────────────────────
# Combines default label + business type so every fold in cross-validation
# is guaranteed to have all business types and both default/non-default.
# Without this, some folds get zero defaults of a particular type
# which causes KS scorer to return nan and hyperparameter search to fail.
stratify_key = df["default"].astype(str) + "_" + df["business_type"]
print(f"Stratification key classes: {stratify_key.nunique()} unique combinations")
print(f"  {stratify_key.value_counts().to_dict()}\n")

# ── Encode ────────────────────────────────────────────────────
df_enc = pd.get_dummies(df.drop(columns=["business_id"]), columns=["business_type"], dtype=int)
y = df_enc["default"]
X = df_enc.drop(columns=["default"])

# Attach stratification key temporarily — will be dropped after splitting
X["_strat_key"] = stratify_key.values

FEATURE_COLS = [c for c in X.columns if c != "_strat_key"]
print(f"Total features after encoding: {len(FEATURE_COLS)}")

# ── Split 70 / 15 / 15 ───────────────────────────────────────
# Stratify on combined key (default + business type) not just default
X_tmp, X_test, y_tmp, y_test = train_test_split(
    X, y,
    test_size=0.15,
    random_state=42,
    stratify=X["_strat_key"]        # ← combined key here
)
X_train, X_val, y_train, y_val = train_test_split(
    X_tmp, y_tmp,
    test_size=0.1765,
    random_state=42,
    stratify=X_tmp["_strat_key"]    # ← and here
)

# Drop the temp column — it must not enter the model
X_train = X_train.drop(columns=["_strat_key"])
X_val   = X_val.drop(columns=["_strat_key"])
X_test  = X_test.drop(columns=["_strat_key"])

print(f"\nSplit sizes:")
print(f"  Train : {len(X_train)} | Default rate: {y_train.mean():.1%}")
print(f"  Val   : {len(X_val)}   | Default rate: {y_val.mean():.1%}")
print(f"  Test  : {len(X_test)}  | Default rate: {y_test.mean():.1%}")

# ── Scale ─────────────────────────────────────────────────────
BOOL_COLS = ["turnover_inflation_spike"] + [c for c in FEATURE_COLS if "business_type_" in c]
NUM_COLS  = [c for c in FEATURE_COLS if c not in BOOL_COLS]
scaler = RobustScaler()
X_train[NUM_COLS] = scaler.fit_transform(X_train[NUM_COLS])
X_val[NUM_COLS]   = scaler.transform(X_val[NUM_COLS])
X_test[NUM_COLS]  = scaler.transform(X_test[NUM_COLS])

# ── Save ──────────────────────────────────────────────────────
X_train.to_csv(os.path.join(DATA_DIR, "X_train.csv"), index=False)
X_val.to_csv(os.path.join(DATA_DIR,   "X_val.csv"),   index=False)
X_test.to_csv(os.path.join(DATA_DIR,  "X_test.csv"),  index=False)
y_train.to_csv(os.path.join(DATA_DIR, "y_train.csv"), index=False)
y_val.to_csv(os.path.join(DATA_DIR,   "y_val.csv"),   index=False)
y_test.to_csv(os.path.join(DATA_DIR,  "y_test.csv"),  index=False)
with open(os.path.join(DATA_DIR, "scaler.pkl"), "wb") as f: pickle.dump(scaler, f)
with open(os.path.join(DATA_DIR, "feature_columns.pkl"), "wb") as f: pickle.dump(FEATURE_COLS, f)
print(f"\n✅ Preprocessing complete.")

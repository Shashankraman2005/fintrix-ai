import pandas as pd
import numpy as np
import logging
import joblib
from xgboost import XGBClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score
from config import XGB_PARAMS, EARLY_STOPPING_ROUNDS, CALIBRATION_METHOD

logger = logging.getLogger(__name__)

def compute_scale_pos_weight(y_train: pd.Series) -> float:
    """
    Computes scale_pos_weight dynamically to mathematically handle class imbalance without SMOTE.
    Formula: count(0s) / count(1s)
    """
    count_0 = (y_train == 0).sum()
    count_1 = (y_train == 1).sum()
    
    scale_pos_weight = count_0 / count_1
    logger.info(f"Computed scale_pos_weight: {scale_pos_weight:.4f} (Class 0: {count_0} / Class 1: {count_1})")
    return float(scale_pos_weight)


def train_xgboost(X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame, y_val: pd.Series) -> XGBClassifier:
    """
    Trains the core XGBoost estimator with defined hyperparams and dynamic scale_pos_weight.
    Includes early stopping based exclusively on validation logloss.
    """
    logger.info("Initializing XGBoost Training...")
    
    params = XGB_PARAMS.copy()
    params['scale_pos_weight'] = compute_scale_pos_weight(y_train)
    params['early_stopping_rounds'] = EARLY_STOPPING_ROUNDS
    
    model = XGBClassifier(**params)
    
    logger.info("Fitting XGBClassifier...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    
    val_probs = model.predict_proba(X_val)[:, 1]
    val_auc = roc_auc_score(y_val, val_probs)
    
    logger.info(f"Training complete! Best iteration: {model.best_iteration}")
    logger.info(f"Validation AUC (raw uncalibrated XGBoost): {val_auc:.4f}")
    
    return model


def calibrate_model(base_model: XGBClassifier, X_val: pd.DataFrame, y_val: pd.Series) -> CalibratedClassifierCV:
    """
    Wraps the trained XGBoost estimator in a CalibratedClassifierCV using Platt Scaling (sigmoid).
    Strictly fitted on validation data to prevent data leakage and overconfidence.
    """
    logger.info(f"Starting model calibration using {CALIBRATION_METHOD} (Platt Scaling) fitted strictly on Val set...")
    
    # Raw predictions to evaluate shift
    raw_probs = base_model.predict_proba(X_val)[:, 1]
    raw_auc = roc_auc_score(y_val, raw_probs)
    
    # Fit Calibration
    calibrated_model = CalibratedClassifierCV(base_model, method=CALIBRATION_METHOD, cv="prefit")    
    calibrated_model.fit(X_val, y_val)
    
    calibrated_probs = calibrated_model.predict_proba(X_val)[:, 1]
    cal_auc = roc_auc_score(y_val, calibrated_probs)
    
    logger.info(f"AUC Shift -> Raw: {raw_auc:.4f} | Calibrated: {cal_auc:.4f}")
    logger.info(f"Prob Range Shift -> Raw: [{raw_probs.min():.4f}, {raw_probs.max():.4f}] | Cal: [{calibrated_probs.min():.4f}, {calibrated_probs.max():.4f}]")
    
    _check_calibration_quality(calibrated_probs, y_val)
    
    return calibrated_model


def _check_calibration_quality(probs: np.ndarray, y_true: pd.Series) -> None:
    """
    Verifies that the generated probabilities reliably reflect true default rates across deciles.
    """
    logger.info("Checking decile-level calibration quality...")
    
    df = pd.DataFrame({'prob': probs, 'actual': y_true.values})
    
    # Bin into deciles (handling duplicate bins drop if tightly clustered)
    df['decile'] = pd.qcut(df['prob'], q=10, duplicates='drop')
    
    summary = df.groupby('decile', observed=True).agg(
        mean_predicted=('prob', 'mean'),
        actual_rate=('actual', 'mean'),
        count=('actual', 'count')
    ).reset_index()
    
    summary['error'] = summary['mean_predicted'] - summary['actual_rate']
    summary['abs_error'] = summary['error'].abs()
    
    # Log formatted table
    print("\n" + "═"*70)
    print(f" {'Decile/Bin':<25} | {'Mean Pred':<10} | {'Actual Rate':<11} | {'Error':<10}")
    print("═" * 70)
    for _, row in summary.iterrows():
        b = str(row['decile'])
        p = row['mean_predicted']
        a = row['actual_rate']
        e = row['error']
        print(f" {b:<25} | {p:<10.4f} | {a:<11.4f} | {e:<10.4f}")
    print("═" * 70 + "\n")
    
    max_err = summary['abs_error'].max()
    if max_err > 0.10:
        logger.warning(f"CALIBRATION CRITICAL WARNING: Max decile absolute error is {max_err:.4f} (Violates > 0.10 limit)")
    else:
        logger.info(f"Calibration quality check passed (Max error = {max_err:.4f} <= 0.10 limit).")


def save_model(model, path: str) -> None:
    logger.info(f"Saving final calibrated model to {path}...")
    joblib.dump(model, path)
    
def load_model(path: str):
    logger.info(f"Loading calibrated model from {path}...")
    return joblib.load(path)

import os
import argparse
import logging
import sys
import pandas as pd
from datetime import datetime

# Import project modules
from config import PREPROCESSOR_PATH, CREDIT_MODEL_PATH, REPORT_DIR, MODEL_DIR, THRESHOLD_APPROVE, THRESHOLD_REVIEW, DATA_PATH
from preprocessor import split_data, build_preprocessor, fit_and_transform, save_preprocessor, load_preprocessor
from trainer import train_xgboost, calibrate_model, save_model, load_model
from evaluator import evaluate_model, compute_global_shap, explain_single_applicant

# Configure dual-channel logging format accurately matching "HH:MM:SS | LEVEL | message"
log_format = "%(asctime)s | %(levelname)s | %(message)s"
date_format = "%H:%M:%S"

# Clear any root handlers to avoid logging crossover with Jupyter/FastAPI runtimes
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    datefmt=date_format,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log", mode='a')
    ]
)
logger = logging.getLogger("ntc_pipeline")


def main():
    parser = argparse.ArgumentParser(description="NTC Alternative Credit Scoring Production Pipeline")
    parser.add_argument("--eval-only", action="store_true", help="Skip training, load models and evaluate cached test set")
    parser.add_argument("--explain", action="store_true", help="Show sample SHAP explanations for 3 applicants after training")
    args = parser.parse_args()

    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    
    if args.eval_only:
        logger.info("\n" + "="*50)
        logger.info("Executing EVAL-ONLY Mode...")
        logger.info("="*50)
        
        logger.info("\n- Step 11/12 (EVAL MODE): Loading model + cached test set...")
        model = load_model(CREDIT_MODEL_PATH)
        X_test_df = pd.read_parquet(os.path.join(MODEL_DIR, "X_test.parquet"))
        y_test = pd.read_parquet(os.path.join(MODEL_DIR, "y_test.parquet"))['TARGET']
        
        logger.info("\n- Step 12: evaluate_model()")
        metrics = evaluate_model(model, X_test_df, y_test)
        
        logger.info("\n- Step 13: compute_global_shap()")
        compute_global_shap(model, X_test_df, X_test_df.columns.tolist())
        
        logger.info("\n- Step 14: Print Final Summary")
        print("\n" + "="*40)
        print(" X EVAL-ONLY PIPELINE SUMMARY")
        print("="*40)
        print(f"ROC AUC:      {metrics['auc']:.4f}")
        print(f"Gini:         {metrics['gini']:.4f}")
        print(f"KS Statistic: {metrics['ks']:.4f}")
        print(f"Brier Score:  {metrics['brier']:.4f}")
        print(f"\nCharts stored in: {REPORT_DIR}")
        print("="*40 + "\n")
        return

    logger.info("\n" + "="*50)
    logger.info("* STARTING NTC FULL PIPELINE BUILD")
    logger.info("="*50)

    logger.info("\n- Step 1: Loading ntc_credit_training_v2.csv directly")
    features_df = pd.read_csv(DATA_PATH)
    logger.info("\n- Step 4: split_data()")
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(features_df)
    
    logger.info("\n- Step 5: Cache X_test + y_test to models/X_test.parquet")
    # For evaluate matching we cache the final transformed Parquets AFTER transform
    # Wait, the prompt says Step 5 caches it here. I will cache the raw one here, and overwrite with transformed at Step 11.
    X_test.to_parquet(os.path.join(MODEL_DIR, "X_test_raw.parquet")) 
    
    logger.info("\n- Step 6: build_preprocessor()")
    preprocessor = build_preprocessor(X_train)
    
    logger.info("\n- Step 7: fit_and_transform()")
    X_train_df, X_val_df, X_test_df = fit_and_transform(preprocessor, X_train, X_val, X_test)
    
    logger.info("\n- Step 8: save_preprocessor()")
    save_preprocessor(preprocessor, PREPROCESSOR_PATH)
    
    logger.info("\n- Step 9: train_xgboost()")
    base_model = train_xgboost(X_train_df, y_train, X_val_df, y_val)
    
    logger.info("\n- Step 10: calibrate_model() using X_val ONLY")
    calibrated_model = calibrate_model(base_model, X_val_df, y_val)
    
    logger.info("\n- Step 11: save_model()")
    save_model(calibrated_model, CREDIT_MODEL_PATH)
    
    # Strictly overwrite cached test set with the actually modeled engineered data
    X_test_df.to_parquet(os.path.join(MODEL_DIR, "X_test.parquet"))
    pd.DataFrame(y_test, columns=['TARGET']).to_parquet(os.path.join(MODEL_DIR, "y_test.parquet"))

    logger.info("\n- Step 12: evaluate_model() on X_test")
    metrics = evaluate_model(calibrated_model, X_test_df, y_test)
    
    logger.info("\n- Step 13: compute_global_shap()")
    compute_global_shap(calibrated_model, X_test_df, X_test_df.columns.tolist())
    
    if args.explain:
        logger.info("\n- EXPLAIN MODE: Fetching Sample SHAP Local Explanations")
        probs = calibrated_model.predict_proba(X_test_df)[:, 1]
        
        test_expl_df = X_test_df.copy()
        test_expl_df['pred_prob'] = probs
        
        def display_shap(condition, tag_name):
            try:
                candidate = test_expl_df[condition]
                if not candidate.empty:
                    idx = candidate.index[0]
                    features_only = candidate.loc[[idx]].drop(columns=['pred_prob'])
                    expl = explain_single_applicant(calibrated_model, features_only, X_test_df.columns.tolist())
                    
                    print(f"\n{tag_name} EXPLANATION:")
                    print("-" * 50)
                    print(f"Prob: {expl['default_probability']:.2%} | Decision: {expl['decision']}")
                    print("Top Drivers:")
                    for idx_r, reason in enumerate(expl['top_reasons']):
                        print(f" {idx_r+1}. [{reason['direction'].upper()}] {reason['feature']} ({reason['impact']:+.4f})")
                    print("-" * 50)
            except Exception as e:
                logger.error(f"Could not generate SHAP for {tag_name}: {e}")

        display_shap(test_expl_df['pred_prob'] < THRESHOLD_APPROVE, "✅ APPROVAL")
        display_shap((test_expl_df['pred_prob'] >= THRESHOLD_APPROVE) & (test_expl_df['pred_prob'] < THRESHOLD_REVIEW), "⚠️ MANUAL REVIEW")
        display_shap(test_expl_df['pred_prob'] >= THRESHOLD_REVIEW, "❌ REJECTION")

    logger.info("\n- Step 14: Print final summary")
    print("\n" + "="*40)
    print(" + FINAL PIPELINE SUMMARY")
    print("="*40)
    print(f"ROC AUC:      {metrics['auc']:.4f}")
    print(f"Gini:         {metrics['gini']:.4f}")
    print(f"KS Statistic: {metrics['ks']:.4f}")
    print(f"Brier Score:  {metrics['brier']:.4f}")
    print(f"\nModel path:  {CREDIT_MODEL_PATH}")
    print(f"Report path: {REPORT_DIR}")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()

# NTC Alternative Credit Scoring System (FintrixAi)

This system provides a production-grade, alternative credit scoring model specifically designed for Indian MSMEs and NTC (New-to-Credit) borrowers using mathematically derived behavioral data. It leverages a strictly calibrated XGBoost architecture with built-in fairness constraints to output robust default probabilities and localized SHAP interpretability.

## Setup
```bash
pip install -r requirements.txt
```

## Run Order
```bash
python ntc_credit_features.py              # generate training data
python main.py                             # train + evaluate
python main.py --explain                   # training + sample explanations
python main.py --eval-only                 # evaluate saved model
python synthetic_transaction_generator.py  # generate demo data
```

## Expected Metrics Targets
* **ROC AUC** > 0.75
* **KS Stat** > 0.35
* **Brier Score** < 0.10

## ⚠️ What NOT to do
* Never add EXT_SOURCE features
* Never use SMOTE
* Never use synthetic transactions for training

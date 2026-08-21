# FintrixAi Alternative Credit Scoring - Project Summary

## 1. Machine Learning & Inference Pipeline
- **Simulation & Training:** Generated realistic MSME / NTC banking data, applied SMOTE to deal with class imbalance, and trained a comprehensive XGBoost risk model.
- **Inference Pipeline:** Layered the model into an automated scoring algorithm combining "pre-layer" hard business rules with backend XGBoost probabilistic scoring.
- **Explainability:** Integrated SHAP to extract raw feature importance determining exact push/pull logic for each credit decision.

## 2. API Backend
- **Account Aggregator (AA) Simulation:** Built entirely encapsulated sandbox routes in FastAPI mapping India's AA consent models (`/aa/users`, `/aa/score`, `/aa/statements`), allowing seamless localized evaluation without API credentials.

## 3. Frontend Implementation
- **React UI:** Built an aesthetically robust, responsive application interface using Vite.
- **Intelligence Dashboard:** Overhauled the Results screen replacing standard numbers with human-readable narratives:
  - **Verdict Card:** Translates rigid metrics (like operating flow and invoice delays) into 2-3 sentence English explanations.
  - **Visual SHAP Breakdown:** Scales algorithmic reasoning into visually colored strength/risk contribution bars.
  - **Decision Charts:** Injected Chart.js locally to synthesize missing timeline gaps, plotting dynamic 6-month trailing Revenue vs Expense simulations alongside an aggregate 6-axis FintrixAi Risk Radar.

## 4. Current State & Blind Batch Evaluation
- Evaluated the pipeline logic directly bridging 100 new LLM-generated edge case scenarios (Wash Traders, Influencers, Seasonal Farmers, etc.).
- **Results:**
  - **Accuracy:** 48.00%
  - **False Positives:** 19 (Good candidates denied)
  - **False Negatives:** 33 (Risky candidates granted)
- **Next Steps:** Given the 33 unseen false negatives (critical risk), model thresholds, pre-layer rule conditions (bounces, cash withdrawal logic), and penalty weightings urgently require fine-tuning calibration to enforce correct boundary separation.

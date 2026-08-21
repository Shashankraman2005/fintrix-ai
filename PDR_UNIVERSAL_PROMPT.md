# PDR Alternative Credit Scoring System — Universal Project Prompt

> **Last updated:** 2026-03-23  
> **Repo:** `github.com/lubdhak123/pdr_2`  
> **Branch:** `main`  
> **Local path:** `C:\Users\kanis\OneDrive\Documents\alternative_credit_scoring\`

---

## 1. PROJECT OVERVIEW

PDR (Proxy Data Rating) is an **alternative credit scoring system** for **Indian MSMEs and NTC (New-To-Credit) borrowers** who lack traditional credit bureau history. Instead of CIBIL scores, PDR uses:

- **Bank statement analysis** (via Account Aggregator framework)
- **GST filing records**
- **Telecom data** (SIM vintage, recharges)
- **Utility payment history**
- **Middleman data** (supplier invoices, BC agent cash deposits)

**Key innovation:** Cash-only MSMEs with NO bank account can be scored using the **Middleman Data Path** — where 5 trusted middlemen (supplier, GST portal, telecom, utility, BC agent) provide data independently.

**Target users:**
- 30 million cash-only MSMEs in India
- NTC individuals with no credit history
- Gig workers, seasonal businesses, micro-retailers

---

## 2. REPOSITORY STRUCTURE

```
alternative_credit_scoring/
│
├── main.py                          # FastAPI app (POST /score, /aa/*, /setu/*)
├── scorer.py                        # Scoring orchestrator (loads models, runs pipeline)
├── feature_engine.py                # Root-level feature extractor (legacy, 32 features)
├── pre_layer.py                     # Rule engine (3 tiers: hard reject, edge case, review)
├── demo_users.json                  # Demo personas for API testing
├── setu_handler.py                  # Real Setu AA integration (sandbox)
├── verify.py                        # Pipeline verification script
├── .gitignore
│
├── ntc_model/                       # ★ MAIN NTC PIPELINE (our primary work)
│   ├── config.py                    #   XGBoost params, thresholds, paths
│   ├── feature_engine.py            #   ★ 44-feature extractor (behavioral + demographic)
│   ├── build_ntc_training_v2.py     #   Training data generator (Home Credit base)
│   ├── data_loader.py               #   CSV → stratified train/val/test split
│   ├── preprocessor.py              #   StandardScaler pipeline
│   ├── trainer.py                   #   XGBoost training with early stopping
│   ├── evaluator.py                 #   AUC, KS, Gini, calibration, SHAP
│   ├── ntc_credit_features.py       #   Feature engineering from Home Credit columns
│   ├── main.py                      #   Orchestrator: load → split → train → evaluate
│   ├── demo_pipeline_test.py        #   Tests 4 demo profiles end-to-end
│   ├── synthetic_transaction_generator.py  # Generates demo bank statements
│   ├── memorization_test.py         #   Detects if model memorized training data
│   ├── real_world_stress_test.py    #   8-scenario stress test
│   ├── test_calib.py                #   Calibration verification
│   │
│   ├── models/                      #   Trained artifacts
│   │   ├── ntc_credit_model.pkl     #   ★ THE NTC XGBoost model
│   │   ├── ntc_preprocessor.pkl     #   StandardScaler fitted on training data
│   │   ├── X_test.parquet           #   Held-out test features
│   │   ├── X_test_raw.parquet       #   Raw (pre-scaled) test features
│   │   └── y_test.parquet           #   Test labels
│   │
│   ├── datasets/
│   │   └── ntc_credit_training_v2.csv  # 44-feature training data (15K rows)
│   │
│   ├── reports/                     #   Evaluation charts
│   │   ├── roc_curve.png
│   │   ├── precision_recall.png
│   │   ├── score_distribution.png
│   │   └── shap_importance.png
│   │
│   └── middleman/                   # ★ MIDDLEMAN DATA PATH (latest addition)
│       ├── __init__.py
│       ├── middleman_feature_engine.py  # Master orchestrator (5 sources → 1 feature vector)
│       ├── test_middleman_path.py       # End-to-end test (4 profiles, all pass)
│       │
│       ├── simulators/              #   Generate realistic demo data
│       │   ├── supplier_simulator.py    # Invoice payment history
│       │   ├── gst_simulator.py         # GSTR-3B filing records
│       │   ├── telecom_simulator.py     # SIM age + recharge history
│       │   ├── utility_simulator.py     # Electricity bill payments
│       │   └── bc_agent_simulator.py    # Cash deposits + field verification
│       │
│       ├── extractors/              #   Parse middleman JSON → credit features
│       │   ├── supplier_extractor.py    # → 12 features (vendor discipline, Benford, etc.)
│       │   ├── gst_extractor.py         # → 5 features (filing consistency, variance, etc.)
│       │   ├── telecom_extractor.py     # → 4 features (SIM vintage, drop ratio, etc.)
│       │   ├── utility_extractor.py     # → 5 features (payment consistency, DPD, etc.)
│       │   └── bc_agent_extractor.py    # → 5 features (buffer, cash dependency, etc.)
│       │
│       └── demo_data/middleman/     #   Generated demo JSON files
│           ├── full_data_good_kirana_*.json     (5 files, 1 per middleman)
│           ├── partial_data_growing_msme_*.json  (3 files)
│           ├── minimal_data_stressed_*.json      (2 files)
│           └── new_business_clean_*.json         (3 files)
│
├── msme_model/                      # MSME pipeline (teammate's work, needs fixing)
│   ├── scripts/
│   │   ├── generate_msme_data.py    #   Synthetic data generator (score-driven labels)
│   │   ├── preprocess.py            #   Feature engineering + train/val/test split
│   │   ├── train.py                 #   XGBoost training with RandomizedSearchCV
│   │   ├── evaluate.py              #   Full evaluation report
│   │   ├── validate.py              #   Business logic validation
│   │   ├── scorecard.py             #   WoE scorecard generation
│   │   └── calibrate_bands.py       #   Score band calibration
│   └── reports/                     #   Evaluation charts
│
├── pdr-frontend/                    # React frontend (Vite)
│   └── src/
│       ├── App.jsx                  #   Main app with 3 screens
│       └── components/
│           ├── Results.jsx          #   Scoring results dashboard
│           ├── Results.css
│           └── UserSelect.jsx       #   User selection screen
│
└── pdr_manual_bridge/               # Manual scoring bridge (legacy)
    ├── manual_score.py
    ├── manual_processor.py
    ├── generate_test_users.py
    └── evaluate_batch.py
```

---

## 3. NTC MODEL — ARCHITECTURE & METRICS

### 3.1 Training Data Generation (`build_ntc_training_v2.py`)

- **Source:** Home Credit dataset (`accepted_2007_to_2018Q4.csv.gz`)
- **Rows:** ~15,000 after filtering
- **TARGET formula:** `0.70 × behavioral_score + 0.30 × demographic_risk + noise → threshold → binary TARGET`
  - **70% behavioral:** utility_payment_consistency, eod_balance_volatility, bounced_transaction_count, etc.
  - **30% demographic:** employment_vintage_days, applicant_age_years, owns_property, income_type_risk_score, etc.
  - This ensures demographics have a consistent, non-random impact on the target variable.
  - Previously used a coin flip; now uses a deterministic demographic risk score.

### 3.2 Feature Set (44 features)

The NTC model uses **44 features** in this exact order:

```
BEHAVIORAL (extracted from bank statements):
 1. utility_payment_consistency     [0,1]    On-time utility payment ratio
 2. avg_utility_dpd                 [0,90]   Average days past due on utilities
 3. rent_wallet_share               [0,1]    Rent+EMI / Income ratio
 4. subscription_commitment_ratio   [0,1]    Fixed subscriptions / Income
 5. emergency_buffer_months         [0,24]   Surplus / Monthly spend
 6. eod_balance_volatility          [0,1]    CV of daily closing balances
 7. essential_vs_lifestyle_ratio    [0,1]    Essential / (Essential+Lifestyle)
 8. cash_withdrawal_dependency      [0,1]    Cash withdrawals / Total debits
 9. bounced_transaction_count       [0,10]   Count of bounced transactions
10. telecom_recharge_drop_ratio     [0,1]    Recent recharge drop vs history
11. min_balance_violation_count     [0,8]    Months below ₹1000 minimum
12. income_stability_score          [0,1]    1 - CV of monthly income
13. income_seasonality_flag         {0,1}    1 if income concentrated in ≤2 months

ALTERNATIVE DATA:
14. telecom_number_vintage_days     [0,3650] Days since SIM activation
15. academic_background_tier        {1..4}   Education level (1=low, 4=PhD)
16. purpose_of_loan_encoded         {1..5}   Loan purpose category

DEMOGRAPHIC (from applicant_metadata):
17. employment_vintage_days         [0,∞]    Days since first salary/employment
18. applicant_age_years             [18,70]  Age in years
19. owns_property                   {0,1}    Flag
20. owns_car                        {0,1}    Flag
21. region_risk_tier                {1..3}   1=low risk, 3=high risk
22. address_stability_years         [0,30]   Years at current address
23. id_document_age_years           [0,30]   Years since ID issued
24. family_burden_ratio             [0,1]    Dependents / Income proxy
25. has_email_flag                   {0,1}    Has email on file
26. income_type_risk_score          {1..5}   1=salaried, 5=unemployed
27. family_status_stability_score   {1..3}   Marital stability proxy
28. contactability_score            {1..3}   Phone + email reachability
29. car_age_years                   [0,99]   99 = no car
30. region_city_risk_score          {1..3}   City-level risk
31. address_work_mismatch           {0,1}    Lives far from workplace
32. employment_to_age_ratio         [0,1]    Employment years / (Age - 18)
33. neighbourhood_default_rate_30   [0,1]    30-day cluster default rate
34. neighbourhood_default_rate_60   [0,1]    60-day cluster default rate

FORENSIC / MSME:
35. p2p_circular_loop_flag          {0,1}    A→B→A money loops detected
36. gst_to_bank_variance            [0,3]    |GST declared - bank credits| / bank
37. customer_concentration_ratio    [0,1]    Revenue from top customer(s)
38. turnover_inflation_spike        {0,1}    Unnatural volume spike pre-application
39. identity_device_mismatch        {0,1}    Multiple accounts same device
40. business_vintage_months         [0,300]  Months since business started
41. gst_filing_consistency_score    [0,12]   Filing streak length
42. revenue_seasonality_index       [0,1]    Gini of monthly revenue
43. revenue_growth_trend            [-1,2]   Recent vs earlier income growth
44. cashflow_volatility             [0,1]    CV of daily net cashflow
```

### 3.3 Model Performance

```
Algorithm     : XGBoost (binary:logistic)
AUC-ROC       : 0.9378
Gini          : 0.8756
KS Statistic  : 0.7262
Calibration   : max error 0.072 (within 0.10 limit)
Stress test   : 8/8 rankings correct
Memorization  : NOT memorized (validated)
```

### 3.4 Decision Thresholds

```python
P(default) < 0.35  → APPROVE
0.35 ≤ P(default) < 0.55  → MANUAL_REVIEW
P(default) ≥ 0.55  → REJECT
```

---

## 4. INFERENCE PIPELINE

### 4.1 AA Path (Digitally Banked Users)

```
POST /score or POST /aa/score
  → scorer.py: score_user(transactions, user_profile, gst_data)
    → feature_engine.py: extract_features(statement)
       - Reads transactions from bank statement JSON
       - Reads applicant_metadata from statement dict
       - Returns 44-feature dict
    → pre_layer.py: apply_pre_layer(features)
       - 3-tier rule engine:
         Type 1: Hard rejection (fraud, extreme stress)
         Type 2: Edge case protection (NRI, seasonal, platform workers)
         Type 3: Manual review triggers
       - Returns override decision OR None (→ model)
    → model.predict_proba(features) → P(default)
    → SHAP explanation (top 5 contributing features)
    → Grade assignment (A+ to F)
```

### 4.2 Middleman Path (Cash-Only MSMEs)

```
POST /score/middleman (TO BE ADDED TO main.py)
  → middleman_feature_engine.py:
      extract_middleman_features(
        supplier_data, gst_data, telecom_data,
        utility_data, bc_agent_data, applicant_metadata
      )
    Step 1: Run available extractors (only for provided data)
    Step 2: Verify minimum 2/5 middlemen (else reject)
    Step 3: Compute confidence (HIGH/MEDIUM/LOW)
    Step 4: Reconcile conflicting features (max, mean rules)
    Step 5: Fill missing features with population defaults
    Step 6: Add demographics from applicant_metadata
    Step 7: Validate (44 features, no None/NaN)
  → Same model, same pre_layer, same decision logic
  → Confidence-adjusted thresholds:
      HIGH (5/5):   APPROVE < 0.35, REVIEW < 0.55
      MEDIUM (3-4): APPROVE < 0.20, REVIEW < 0.50
      LOW (2):      APPROVE < 0.15, REVIEW < 0.45
```

### 4.3 The 5 Middlemen

| # | Middleman | What It Provides | Features Extracted |
|---|-----------|------------------|--------------------|
| 1 | **Supplier/Wholesaler** | Invoice payment history | vendor_payment_discipline, avg_invoice_payment_delay, cashflow_volatility, revenue_growth_trend, Benford score, round number ratio |
| 2 | **GST Portal** | GSTR-3B filing records | gst_filing_consistency_score, gst_to_bank_variance, revenue_seasonality_index, business_vintage_months |
| 3 | **Telecom Operator** | SIM age, recharge history | telecom_number_vintage_days, telecom_recharge_drop_ratio, identity_device_mismatch |
| 4 | **Utility Company** | Electricity/water bills | utility_payment_consistency, avg_utility_dpd, min_balance_violation_count, eod_balance_volatility |
| 5 | **BC Agent/Kirana** | Cash deposits, field verification | emergency_buffer_months, cash_withdrawal_dependency, bounced_transaction_count, identity_device_mismatch |

### 4.4 Middleman Demo Profiles

| Profile | Sources | Confidence | P(default) | Decision |
|---------|---------|-----------|------------|----------|
| `full_data_good_kirana` | 5/5 | HIGH | 0.0229 | APPROVE ✓ |
| `partial_data_growing_msme` | 3/5 | MEDIUM | 0.2728 | MANUAL_REVIEW ✓ |
| `minimal_data_stressed` | 2/5 | LOW | 0.8730 | REJECT ✓ |
| `new_business_clean` | 3/5 | MEDIUM | 0.2498 | MANUAL_REVIEW ✓ |

---

## 5. PRE-LAYER RULE ENGINE (`pre_layer.py`)

384-line rule engine with thresholds from RBI, CIBIL, and NABARD. Three tiers:

### Type 1 — Hard Rejection (unambiguous fraud/extreme stress)
- P2P circular flow + bounced transactions
- GST variance > 150% (material misrepresentation)
- 5+ bounces (chronic inability)
- 3+ minimum balance violations
- >80% cash dependency + bounces

### Type 2 — Edge Case Protection (legitimate non-standard profiles)
- NRI/platform worker with low cash dependency
- Seasonal business with legitimate GST filings
- New business with strong telecom vintage + clean GST
- High-value stable borrower with minor utility delays

### Type 3 — Manual Review Triggers
- High customer concentration (>85% from 1-2 clients)
- Region risk + cashflow volatility combo
- Income drop > 30% with low buffer
- Moderate bounce count with digital payments

---

## 6. FASTAPI ENDPOINTS (`main.py`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST /score` | Direct scoring (transactions + profile + GST) |
| `GET /health` | Health check (model loaded, Setu ready) |
| `GET /demo/{user_id}` | Score a demo user by ID |
| `GET /aa/health` | AA simulation health |
| `GET /aa/users` | List all demo users |
| `POST /aa/users/{uid}/consent` | Grant data access consent |
| `GET /aa/users/{uid}/profile` | Fetch user profile data |
| `GET /aa/users/{uid}/statements` | Fetch bank statements |
| `POST /aa/score` | Full AA-style scoring |
| `POST /setu/consent` | Real Setu AA consent (sandbox) |
| `POST /setu/score` | Real Setu FI data fetch + score |
| `GET /setu/consent/{id}/status` | Check consent status |

**TO BE ADDED (middleman path):**
| `POST /score/middleman` | Score cash-only MSME via middlemen |
| `GET /middleman/consent/{msme_id}` | Simulated consent status |
| `GET /middleman/data/{msme_id}/{source}` | Serve demo middleman data |

---

## 7. FRONTEND (`pdr-frontend/`)

- **Framework:** React + Vite
- **3 Screens:**
  1. **Landing page:** Project overview, key stats
  2. **User selection:** Choose demo persona to score
  3. **Results dashboard:** Score, grade, SHAP explanations, risk factors
- **Backend connection:** `http://localhost:8000`
- **Run:** `cd pdr-frontend && npm run dev`

---

## 8. MSME MODEL — STATUS & ISSUES

The MSME model (in `msme_model/`) was built by a teammate. **Current status: BROKEN.**

```
Test AUC    : 0.5865 (near random — should be >0.80)
Gini        : 0.1730
KS          : 0.2240
Best CV KS  : NaN (scoring bug in cross-validation)
```

**Root causes:**
1. Training was interrupted (KeyboardInterrupt in log)
2. Best iteration = 4 (model barely trained before early stopping)
3. KS scorer returns NaN for single-class CV folds
4. Features: 12 MSME-specific (business_vintage, operating_cashflow_ratio, gst_filing_consistency, etc.)

**MSME features (12):**
```
business_vintage_months, revenue_growth_trend, revenue_seasonality_index,
operating_cashflow_ratio, cashflow_volatility, avg_invoice_payment_delay,
customer_concentration_ratio, repeat_customer_revenue_pct,
vendor_payment_discipline, gst_filing_consistency_score,
gst_to_bank_variance, turnover_inflation_spike
```

**To fix:** Retrain with proper early stopping, fix KS scorer NaN handling, run full evaluation.

---

## 9. KNOWN ISSUES & TECH DEBT

| Priority | Issue | Details |
|----------|-------|---------|
| 🔴 HIGH | MSME model AUC = 0.59 | Near random, needs full retraining |
| 🔴 HIGH | `node_modules/` in git | Someone pushed 130K lines of vendor code; need `.gitignore` update |
| 🟡 MED | `eda_validate.py` has Linux paths | Uses `/mnt/user-data/outputs/...` — won't run on Windows |
| 🟡 MED | Root `scorer.py` loads old models | Lines 34-35 load `pdr_ntc_model.pkl` and `pdr_msme_model.pkl` (root-level, possibly outdated) |
| 🟡 MED | Middleman endpoints not yet in `main.py` | `POST /score/middleman` etc. defined but not added to FastAPI app |
| 🟢 LOW | `demo_pipeline_test.py` profile 2 | `stressed_gig_ntc` gets REJECT (73%) but expected MANUAL_REVIEW — debatable with demographics factored in |

---

## 10. DEPENDENCIES

```
Python 3.13+
numpy, pandas, scikit-learn, xgboost, shap, joblib
fastapi, uvicorn, pydantic
python-dateutil
requests (for Setu AA)
matplotlib, seaborn (for reports)
```

---

## 11. HOW TO RUN

### Backend
```bash
cd alternative_credit_scoring
pip install fastapi uvicorn pandas numpy scikit-learn xgboost shap joblib python-dateutil
python main.py
# API runs at http://localhost:8000
```

### NTC Model Training
```bash
cd ntc_model
python main.py
# Generates training data → trains XGBoost → evaluates → saves to models/
```

### Middleman Path Test
```bash
cd ntc_model
python middleman/simulators/supplier_simulator.py
python middleman/simulators/gst_simulator.py
python middleman/simulators/telecom_simulator.py
python middleman/simulators/utility_simulator.py
python middleman/simulators/bc_agent_simulator.py
python middleman/test_middleman_path.py
# Expected: 4/4 profiles correct, pipeline READY
```

### Frontend
```bash
cd pdr-frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

---

## 12. KEY DESIGN DECISIONS

1. **70/30 behavioral-demographic split:** TARGET = 0.70 × behavioral_score + 0.30 × demographic_risk. Adjustable.

2. **Single model for both paths:** The AA path and Middleman path use the SAME XGBoost model. Middleman merely provides a different way to populate the same 44-feature vector.

3. **Confidence-adjusted thresholds:** Middleman path with fewer data sources uses tighter APPROVE bars. Less data = less certainty = more human review.

4. **Population defaults for missing features:** When a middleman isn't available, its features get neutral population-average values (not zeros, which would bias the model).

5. **Pre-layer overrides ML:** Hard fraud signals bypass the model entirely. The rule engine fires BEFORE the model.

6. **No coin flip in training:** The old data generation used `rng.random() < noise` to assign defaults, causing good borrowers to be randomly flagged. Now uses a deterministic demographic risk score.

---

## 13. NEXT STEPS

1. **Add middleman endpoints to main.py** (`POST /score/middleman`, etc.)
2. **Fix MSME model** (retrain with proper parameters)
3. **Add `node_modules/` to `.gitignore`** and remove from tracking
4. **Frontend integration** for middleman scoring flow
5. **Real Setu AA testing** with sandbox credentials
6. **Scorecard report generation** (WoE-based scoring card for regulators)
7. **Production deployment** (Docker, cloud hosting)

---

## 14. HACKATHON CONTEXT

- **Event:** Hackathon (8 days remaining as of 2026-03-23)
- **Team:** lubdhak123 + collaborator (Rayirth556)
- **Pitch:** "30 million cash-only MSMEs can now access credit. No bank account needed. No UPI history needed. No AA data needed. Scored using middleman data only. Same model. Same pipeline. Same decision quality."

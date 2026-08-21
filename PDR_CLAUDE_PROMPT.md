# PDR Alternative Credit Scoring System — Complete Context Prompt

> **Last updated:** 2026-03-25 13:19 IST
> **Repo:** `github.com/lubdhak123/pdr_2`
> **Branch:** `main`
> **Local path:** `C:\Users\kanis\OneDrive\Documents\alternative_credit_scoring\`
> **Hackathon:** ~7 days remaining

---

## 1. PROJECT OVERVIEW

PDR (Proxy Data Rating) is an **alternative credit scoring system** for **Indian MSMEs and NTC (New-To-Credit) borrowers** who lack CIBIL scores. Uses:

- Bank statement analysis (via Account Aggregator framework)
- GST filing records
- Telecom data (SIM vintage, recharges)
- Utility payment history
- Middleman data (supplier invoices, BC agent cash deposits)

**Key innovation:** Cash-only MSMEs with NO bank account scored via **Middleman Data Path** — 5 trusted middlemen provide data independently.

**Target users:** 30 million cash-only MSMEs, NTC individuals, gig workers, seasonal businesses.

**Tech stack:** FastAPI backend, React frontend, XGBoost + Platt Scaling, SHAP TreeExplainer.

---

## 2. REPOSITORY STRUCTURE

```
alternative_credit_scoring/
├── main.py                          # FastAPI app
├── scorer.py                        # Scoring orchestrator
├── feature_engine.py                # Root-level feature extractor (legacy)
├── pre_layer.py                     # Rule engine (3 tiers)
├── demo_users.json                  # Demo personas
├── setu_handler.py                  # Real Setu AA integration
├── application_train.csv            # Home Credit demographics (307K rows)
│
├── ntc_model/                       # ★ MAIN NTC PIPELINE
│   ├── config.py                    #   XGBoost params, thresholds
│   ├── feature_engine.py            #   ★ 49-feature extractor
│   ├── build_ntc_training_v3.py     #   ★ REAL DATA training generator (cs-training + Home Credit)
│   ├── build_ntc_training_v2.py     #   OLD synthetic training generator (deprecated)
│   ├── data_loader.py               #   CSV → stratified split
│   ├── preprocessor.py              #   StandardScaler pipeline
│   ├── trainer.py                   #   XGBoost training
│   ├── evaluator.py                 #   AUC, KS, Gini, SHAP
│   ├── main.py                      #   Orchestrator
│   ├── circularity_diagnostic.py    #   ★ Proves circularity is broken
│   ├── honest_assessment.py         #   ★ Full assessment (memorization, real data, feature importance)
│   ├── demo_pipeline_test.py        #   4 demo profiles end-to-end
│   ├── real_world_stress_test.py    #   10-scenario stress test
│   │
│   ├── models/
│   │   ├── ntc_credit_model.pkl     #   ★ THE NTC XGBoost model (retrained on real data)
│   │   ├── ntc_preprocessor.pkl     #   StandardScaler
│   │   ├── X_test.parquet           #   Test features
│   │   └── y_test.parquet           #   Test labels
│   │
│   ├── datasets/
│   │   └── ntc_credit_training_v2.csv  # 49-feature training data (25K rows, REAL behavioral)
│   │
│   ├── middleman/                   # ★ MIDDLEMAN DATA PATH
│   │   ├── middleman_feature_engine.py  # 5 sources → 1 feature vector
│   │   ├── test_middleman_path.py
│   │   ├── simulators/  (supplier, gst, telecom, utility, bc_agent)
│   │   ├── extractors/  (supplier, gst, telecom, utility, bc_agent)
│   │   └── demo_data/   (4 profiles × 5 middlemen)
│   │
│   ├── circ_out.txt                 # Circularity diagnostic output
│   ├── honest_assessment.txt        # Full assessment output
│   └── source_audit.txt             # Feature source traceability
│
├── msme_model/                      # MSME pipeline (needs fixing, AUC=0.59)
├── pdr-frontend/                    # React frontend (Vite)
└── pdr_manual_bridge/               # Legacy manual scoring
```

---

## 3. DATASETS

### 3.1 Training Data Sources

| Dataset | Location | Rows | What It Provides |
|---------|----------|------|-----------------|
| **cs-training.csv** ★ | `Desktop\ecirricula\datasets\new dataset\archive (1)\` | **150,000** | **REAL behavioral features** (DPD, utilization, debt ratio) + **REAL TARGET** (2-year default) |
| **application_train.csv** | Root of repo | **307,511** | Demographics (age, employment, education, property, income type) — from Home Credit |
| **loan_dataset_20000.csv** | Same archive folder | **20,000** | Demographics + behavioral + loan details + REAL repayment outcome |
| **upi_transactions_2024.csv** | `Desktop\ecirricula\datasets\new dataset\` | **250,000** | Indian UPI transactions — used for **calibration constants** only |
| **MyTransaction.csv** | Same folder | **1,471** | Single real person's bank statement — used for **real-world pipeline test** |
| **transactions.csv** | Same folder | **1,001** | UPI P2P transfers — used for circular loop detection analysis |

### 3.2 cs-training.csv — The Critical Dataset (Kaggle "Give Me Some Credit")

This is what **broke the circularity**. Each row = 1 person with:
```
SeriousDlqin2yrs                    → TARGET (REAL 2-year delinquency flag, 6.7% rate)
RevolvingUtilizationOfUnsecuredLines → eod_balance_volatility, cashflow_volatility
age                                 → applicant_age_years
NumberOfTime30-59DaysPastDueNotWorse → bounced_transaction_count, avg_utility_dpd
NumberOfTime60-89DaysPastDueNotWorse → telecom_recharge_drop_ratio
NumberOfTimes90DaysLate              → min_balance_violation_count
DebtRatio                           → rent_wallet_share, emergency_buffer_months
MonthlyIncome                       → emergency_buffer_months
NumberOfOpenCreditLinesAndLoans      → customer_concentration_ratio, business_vintage_months
NumberRealEstateLoansOrLines         → owns_property
NumberOfDependents                   → family_burden_ratio
```

After cleaning (remove nulls, age outliers, extreme ratios): **117,799 clean rows**.

### 3.3 UPI Dataset — Used for Calibration Only

**Cannot be used for per-user behavioral features** because:
- Each row = 1 transaction, NOT 1 person
- No user_id column → cannot group transactions by person
- Only 5 age groups × 10 states × 8 banks × 3 devices = 1,200 combos max
- 250K transactions / 1,200 combos = ~208 different people per combo

**What we extracted from UPI (aggregate statistics only):**
```python
UPI_NIGHT_TXN_RATIO   = 0.0465   # % of transactions 12AM-6AM
UPI_WEEKEND_RATIO     = 0.2853   # % of spending on weekends
UPI_PAYMENT_DIVERSITY = 0.8374   # mix of P2P/P2M/Bill/Recharge
UPI_ESSENTIAL_RATIO   = 0.5509   # essential vs lifestyle spending
UPI_FAILURE_RATE      = 0.0495   # transaction failure rate (4.95%)
UPI_FRAUD_RATE        = 480/250K # fraud flag rate
```

---

## 4. THE CIRCULARITY PROBLEM AND HOW WE FIXED IT

### 4.1 The Original Problem (identified by Claude)

```
v1 (CIRCULAR):
  demo_risk = f(age, employment, property, education)
  behavioral_feature_mean = f(demo_risk)         ← ALL behavioral derived from demographics
  TARGET = f(behavioral_features)                 ← = f(f(demographics))
  
  XGBoost sees: age=42 → high utility_consistency → TARGET=0
  Result: Model learns demographics→demographics, behavioral features are redundant
  Evidence: TARGET ↔ demo_risk correlation = 0.52, demo-only AUC = 0.83
```

### 4.2 Failed Fix Attempt (v2 — independent noise)

```
v2 (NOISE FIX):
  behav_risk = Beta(2.5, 2.5)                     ← independent random variable
  mixed_risk = 0.80 * behav_risk + 0.20 * demo_risk
  behavioral_feature_mean = f(mixed_risk)
  TARGET = 0.60 * behavioral + 0.25 * demographic + 0.15 * noise
  
  Problem: behav_risk is still RANDOM NOISE, not real behavior
  Claude: "The 65% is just random Gaussian noise. It has no meaning."
  Evidence: TARGET ↔ demo_risk dropped to 0.37, but behavioral features still synthetic
```

### 4.3 The Real Fix (v3 — cs-training.csv real data)

```
v3 (REAL DATA):
  behavioral = REAL measurements from cs-training.csv (DPD counts, utilization, debt ratio)
  TARGET = REAL 2-year delinquency flag (SeriousDlqin2yrs)
  demographics = Home Credit, RANDOMLY PAIRED (different people → independent!)
  
  Result: behavioral ≠ f(demographics) because they come from DIFFERENT datasets
  Evidence: TARGET ↔ demo_risk = 0.08, demo-only AUC = 0.64
```

### 4.4 Circularity Diagnostic Results (all three versions)

| Metric | v1 (circular) | v2 (noise) | **v3 (REAL)** |
|--------|:------------:|:----------:|:-------------:|
| TARGET ↔ demo_risk correlation | **0.52** | 0.37 | **0.08** |
| Demo-only AUC | **0.83** | 0.74 | **0.64** |
| Behavioral-only AUC | 0.89 | 0.81 | **0.85** |
| Combined AUC | 0.90 | 0.86 | **0.85** |
| **Behavioral lift over demographics** | +0.07 | +0.13 | **+0.21** |
| Circular features (|corr| > 0.50) | many | 0/18 | **0/18** |

---

## 5. NTC MODEL v3 — ARCHITECTURE & METRICS

### 5.1 Training Data Generation (`build_ntc_training_v3.py`)

```
Step 1: Load cs-training.csv (150K real credit records)
Step 2: Clean (remove nulls, outliers) → 117K clean rows
Step 3: Stratified sample: 5K defaults + 20K non-defaults = 25K rows (20% default rate)
Step 4: Map cs-training behavioral columns → our 49-feature schema
Step 5: Load Home Credit (307K rows), sample 25K RANDOMLY (independent of cs-training)
Step 6: Map Home Credit → demographic features
Step 7: TARGET = SeriousDlqin2yrs (REAL, not synthetic)
```

**Critical design:** Demographics from Home Credit are randomly paired with behavioral from cs-training. These are DIFFERENT people. This is INTENTIONAL — it guarantees demographics cannot predict behavioral features, breaking circularity.

### 5.2 Feature Set (49 features)

```
BEHAVIORAL — from REAL cs-training.csv data (no random generation):
  1. utility_payment_consistency     [0,1]    1 - total_DPD_count/20 (REAL)
  2. avg_utility_dpd                 [0,90]   30DPD*5 + 60DPD*10 + 90DPD*15 (REAL)
  3. rent_wallet_share               [0,1]    DebtRatio clipped to [0,1] (REAL)
  4. subscription_commitment_ratio   [0,1]    rent_wallet_share * 0.3 (derived from real)
  5. emergency_buffer_months         [0,24]   (income-debt)/income*6 (REAL)
  6. eod_balance_volatility          [0,1]    RevolvingUtilization clipped (REAL)
  7. essential_vs_lifestyle_ratio    [0,1]    0.80 - RevolvingUtil*0.40 (derived)
  8. cash_withdrawal_dependency      [0,1]    RevolvingUtil * 0.7 (derived)
  9. bounced_transaction_count       [0,10]   NumberOfTime30-59DPD (REAL DIRECT)
 10. telecom_recharge_drop_ratio     [0,1]    NumberOfTime60-89DPD / 10 (REAL)
 11. min_balance_violation_count     [0,8]    NumberOfTimes90DaysLate (REAL DIRECT)
 12. income_stability_score          [0,1]    1 - total_DPD/15 (derived from real)
 13. income_seasonality_flag         {0,1}    30-59DPD >= 3 (threshold on real)

FORENSIC / MSME — derived from REAL behavioral signals:
 14. p2p_circular_loop_flag          {0,1}    util>0.8 AND total_late>=4 (real)
 15. gst_to_bank_variance            [0,3]    DebtRatio * 0.8 (real)
 16. customer_concentration_ratio    [0,1]    1 - OpenCreditLines/20 (real)
 17. turnover_inflation_spike        {0,1}    DebtRatio > 2.0 (real)
 18. identity_device_mismatch        {0,1}    util>0.9 AND 90DPD>=2 (real)
 19. business_vintage_months         [0,300]  OpenCreditLines * 8 (real)
 20. gst_filing_consistency_score    [0,12]   12 - total_DPD*0.8 (derived)
 21. revenue_seasonality_index       [0,1]    total_DPD / 20 (derived)
 22. revenue_growth_trend            [-1,2]   0.10 - 90DPD*0.05 (derived)
 23. cashflow_volatility             [0,1]    RevolvingUtil * 0.8 (derived)

UPI-CALIBRATED (baselines from 250K UPI + shift from real DPD severity):
 24. night_transaction_ratio         [0,1]    UPI_baseline + behav_risk*0.08
 25. weekend_spending_ratio          [0,1]    UPI_baseline + behav_risk*0.06
 26. payment_diversity_score         [0,1]    UPI_baseline - behav_risk*0.25
 27. device_consistency_score        [0,1]    0.85 - behav_risk*0.25
 28. geographic_risk_score           {1,2,3}  rng.choice(p=f(behav_risk))

DEMOGRAPHIC — from Home Credit (INDEPENDENTLY sampled):
 29. applicant_age_years             [21,70]  From cs-training age (REAL)
 30. employment_vintage_days         [0,18250] From Home Credit DAYS_EMPLOYED
 31. academic_background_tier        {1..5}   From Home Credit NAME_EDUCATION_TYPE
 32. owns_property                   {0,1}    cs-training RealEstateLoans > 0 (REAL)
 33. owns_car                        {0,1}    Home Credit FLAG_OWN_CAR
 34. region_risk_tier                {1..3}   Home Credit REGION_RATING_CLIENT
 35. address_stability_years         [0.5,30] Derived from age
 36. id_document_age_years           [1,50]   Derived from age
 37. family_burden_ratio             [0,1]    cs-training Dependents/5 (REAL)
 38. income_type_risk_score          {1..5}   Home Credit NAME_INCOME_TYPE
 39. family_status_stability_score   {1..3}   Home Credit NAME_FAMILY_STATUS
 40. contactability_score            {0..4}   cs-training OpenCreditLines/5 (REAL)
 41. purpose_of_loan_encoded         {1..3}   Random (not predictive)
 42. car_age_years                   [0,99]   Home Credit OWN_CAR_AGE
 43. region_city_risk_score          {1..3}   Home Credit REGION_RATING_CLIENT_W_CITY
 44. address_work_mismatch           {0,1}    Home Credit REG_CITY_NOT_WORK_CITY
 45. has_email_flag                   {0,1}    Home Credit FLAG_EMAIL
 46. telecom_number_vintage_days     [0,3650] Home Credit DAYS_LAST_PHONE_CHANGE
 47. neighbourhood_default_rate_30   [0,1]    Home Credit social circle defaults
 48. neighbourhood_default_rate_60   [0,1]    Home Credit social circle defaults

DERIVED:
 49. employment_to_age_ratio         [0,1]    employment_vintage / (age-18)*365

TARGET: SeriousDlqin2yrs from cs-training.csv (REAL 2-year default, NOT synthetic)
```

### 5.3 Feature Source Audit

Every behavioral feature was traced to its origin. Results:

| Source Type | Count | Description |
|-------------|-------|-------------|
| **REAL** (directly from cs-training) | 11/28 | DPD counts, utilization, debt ratio, income |
| **DERIVED** (transform of real data) | 9/28 | Inverse, threshold, scale of real data — no randomness |
| **MIXED** (real signal + UPI calibration) | 7/28 | UPI baseline + real DPD severity shift |
| **PURE RANDOM** | **0/28** | None |

### 5.4 Model Performance (v3)

```
Algorithm     : XGBoost (binary:logistic) + Platt Scaling
Training rows : 25,000 (from 150K cs-training + 307K Home Credit)
Features      : 49
Default rate  : 20.0% (oversampled from natural 6.7%)

AUC-ROC       : 0.8499
Gini          : 0.6998
Brier Score   : 0.1118
KS Statistic  : 0.5440
```

### 5.5 Decision Thresholds

```python
P(default) < 0.35  → APPROVE
0.35 ≤ P(default) < 0.55  → MANUAL_REVIEW
P(default) ≥ 0.55  → REJECT
```

---

## 6. TESTS AND VALIDATION

### 6.1 Memorization Test — PASS

```
Test: Perturb behavioral features while keeping demographics fixed.
If model memorized demographics, behavioral perturbation won't matter.

Good behavioral P(default):    9.7%
Base P(default):               4.2%
Bad behavioral P(default):    37.2%
Behavioral swing:             +27.5%   ← model responds to behavior
Demographic swing:             +1.3%   ← demographics barely matter
Behavioral / Demographic:     22.0x    ← behavior 22x more important
```

### 6.2 Contradiction Test — PASS

```
Good behavior + Bad demographics:  P(def) = 16.4%
Bad behavior + Good demographics:  P(def) = 27.8%

PASS: A 55-year-old property owner with bad payment history
      gets HIGHER risk than a 22-year-old renter with clean payments.
      Model correctly prioritizes behavior over demographics.
```

### 6.3 Real Data Test (MyTransaction.csv) — PASS

```
Real bank data extracted features:
  monthly_income:              ₹6,950
  monthly_expense:             ₹13,236 (2x income!)
  rent_wallet_share:           0.518
  emergency_buffer_months:     0.000 (zero buffer)
  eod_balance_volatility:      0.857 (wild swings)
  income_stability_score:      0.000 (completely erratic)
  min_balance_violations:      8 (maximum)

MODEL PREDICTION: P(default) = 63.5% → REJECT
EXPECTED: HIGH RISK (spending 2x income, zero buffer)
RESULT: CORRECT ✅
```

### 6.4 Feature Importance

```
Demographic features:  10.9%   ← negligible
Behavioral features:   89.1%   ← dominant
Ratio (behav/demo):    8.20x

Top 10 features (ALL behavioral):
  1. gst_filing_consistency_score    32.8%   (from real DPD data)
  2. utility_payment_consistency     26.0%   (from real DPD data)
  3. avg_utility_dpd                  7.0%   (from real DPD data)
  4. income_stability_score           5.4%   (from real DPD data)
  5. essential_vs_lifestyle_ratio     3.5%   (from real utilization)
  6. cashflow_volatility              2.9%   (from real utilization)
  7. eod_balance_volatility           2.5%   (from real utilization)
  8. cash_withdrawal_dependency       1.9%   (from real utilization)
  9. emergency_buffer_months          0.9%   (from real income+debt)
 10. gst_to_bank_variance             0.9%   (from real debt ratio)

Demographics in top 10: ZERO
```

### 6.5 Circularity Diagnostic Summary

```
Circular features (|corr| > 0.50):  0/18
TARGET vs demo_risk correlation:    0.0783  (was 0.52 → now near zero)
Demographics-only AUC:              0.6428  (was 0.83 → barely above random)
Behavioral-only AUC:                0.8481  (carries all the signal)
Behavioral lift:                    +0.2067 (was +0.07 → 3x improvement)
```

---

## 7. PRE-LAYER RULE ENGINE (`pre_layer.py`)

~480-line rule engine with 20 rules. Three tiers. Returns None if no rule fires → ML model runs.
All thresholds sourced from RBI Master Directions, TransUnion CIBIL MSME Credit Health Index, NABARD Financial Inclusion Report.

### Type 1 — Hard Rejection (6 rules)
| # | Rule | Trigger |
|---|------|---------|
| 1 | Seasonal spike protection | `seasonality>0.60 + GST>=4 + GST_variance>1.5 + 0 bounces` → MANUAL REVIEW (not reject) |
| 2 | Circular fund flow + bounces | `p2p_circular=1 + bounces>=3` → REJECT |
| 3 | GST turnover inflation | `gst_variance > 1.5` → REJECT |
| 4 | Excessive bounces | `bounces >= 5` → REJECT |
| 5 | Balance inflation + new SIM | `eod_volatility>0.85 + SIM<120d + utility_consistency<0.30` → REJECT |
| 6 | Identity fraud combo | `identity_mismatch + SIM<120d + GST=0 + bounces>=1` → REJECT |
| 7 | Severe liquidity failure | `min_bal_violations>=3` → REJECT (exempt: seasonal farmers with 0 bounces) |
| 8 | Extreme cash + bounces | `cash_dependency>0.80 + bounces>=3` → REJECT |

### Type 2 — Edge Case Protection (4 rules)
| # | Rule | Decision |
|---|------|----------|
| 9 | Clean established business | `0 bounces + SIM>1000d + GST>=6 + utility>0.85 + cash<0.15` → A/APPROVED |
| 10 | Seasonal/agricultural income | `0 bounces + SIM>1000d + GST_var<0.8 + GST>0` → B/APPROVED WITH CONDITIONS |
| 11 | NRI/platform/remittance | `GST=0 + 0 bounces + cash<0.20 + SIM>500d` → B/APPROVED WITH CONDITIONS |
| 12 | New business strong signals | `vintage<=12mo + 0 bounces + SIM>1500d + buffer>2mo` → B/APPROVED WITH CONDITIONS |

### Type 3 — Manual Review (8 rules)
| # | Rule | Trigger |
|---|------|---------|
| 13 | P2P circular + any bounces | `p2p_circular=1 + bounces>=1` → REVIEW |
| 14 | P2P circular alone | `p2p_circular=1` → REVIEW |
| 15 | Zero-signal profile | `<=1 signal out of 7` → REVIEW |
| 16 | Customer concentration | `concentration>0.85 + risk signals` → REVIEW |
| 17 | Turnover inflation spike | `turnover_spike=1` → REVIEW |
| 18 | Identity mismatch | `identity_mismatch=1` → REVIEW |
| 19 | Declining established business | `growth<-0.40 + vintage>24mo + buffer<2mo` → REVIEW |
| 20 | Chronic late payer | `avg_DPD>20 + 0 bounces + utility<0.50` → REVIEW |
| 21 | Seasonal farmer min_bal | `seasonality>0.60 + min_bal>=3 + 0 bounces + SIM>1000d` → REVIEW |
| 22 | Gig worker partial GST | `seasonal_flag + stability<0.40 + 0 bounces + GST 1-5` → REVIEW |

### 7.1 Demo User Test Results (ALL PASSING)

```
NTC_001 (Clean Salaried)      → [PL] APPROVED WITH CONDITIONS  ✅
NTC_002 (Cash-Dependent)      → [PL] REJECTED (min_bal=5)      ✅
NTC_003 (Balance Inflation)   → [PL] MANUAL REVIEW (P2P circ)  ✅
MSME_001 (Seasonal Farmer)    → [ML] APPROVED (P=30.8%)        ✅
MSME_002 (Wash Trader)        → [PL] MANUAL REVIEW (P2P+bounce)✅
```

### 7.2 Edge Case Test Results (ALL PASSING)

```
High-value stable borrower    → [PL] B/APPROVED WITH CONDITIONS ✅
Gig worker UPI-only           → [PL] B/APPROVED WITH CONDITIONS ✅
Retired person (pension)      → [ML] APPROVED (P=17.6%)        ✅
Student part-time             → [PL] B/APPROVED WITH CONDITIONS ✅
Farmer 3 min_bal violations   → [PL] C/MANUAL REVIEW           ✅ (was REJECTED)
High cash just below 0.80     → [ML] MANUAL_REVIEW (P=40.0%)   ✅
P2P circular <3 bounces       → [PL] C/MANUAL REVIEW           ✅ (was APPROVED)
Zero-signal empty account     → [PL] C/MANUAL REVIEW           ✅ (was APPROVED)
```

---

## 8. MIDDLEMAN DATA PATH (Cash-Only MSMEs)

### 8.1 Architecture

5 middlemen provide data independently for MSMEs with no bank account:

| # | Middleman | Features Extracted |
|---|-----------|-------------------|
| 1 | Supplier/Wholesaler | vendor_discipline, invoice_delay, cashflow, revenue_growth, Benford, round_number |
| 2 | GST Portal | filing_consistency, gst_variance, revenue_seasonality, business_vintage |
| 3 | Telecom Operator | SIM_vintage, recharge_drop, identity_device_mismatch |
| 4 | Utility Company | payment_consistency, avg_DPD, min_balance_violations, balance_volatility |
| 5 | BC Agent/Kirana | emergency_buffer, cash_dependency, bounced_count, identity_mismatch |

### 8.2 Demo Profiles (ALL PASSING)

| Profile | Sources | Confidence | P(default) | Decision |
|---------|---------|-----------|------------|----------|
| full_data_good_kirana | 5/5 | HIGH | 0.023 | APPROVE ✓ |
| partial_data_growing_msme | 3/5 | MEDIUM | 0.273 | MANUAL_REVIEW ✓ |
| minimal_data_stressed | 2/5 | LOW | 0.873 | REJECT ✓ |
| new_business_clean | 3/5 | MEDIUM | 0.250 | MANUAL_REVIEW ✓ |

---

## 9. FASTAPI ENDPOINTS (`main.py`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST /score | Direct scoring |
| GET /health | Health check |
| GET /demo/{user_id} | Score demo user |
| GET /aa/health | AA simulation |
| GET /aa/users | List demo users |
| POST /aa/users/{uid}/consent | Grant consent |
| GET /aa/users/{uid}/profile | User profile |
| GET /aa/users/{uid}/statements | Bank statements |
| POST /aa/score | Full AA scoring |
| POST /setu/consent | Real Setu AA |
| POST /setu/score | Setu FI + score |

**TO BE ADDED:** POST /score/middleman

---

## 10. KNOWN ISSUES & HONEST LIMITATIONS

### 10.1 Resolved Issues

| Issue | Status | Evidence |
|-------|--------|---------|
| Circular dependency (behavioral = f(demographics)) | **FIXED** | TARGET↔demo corr: 0.52 → 0.08 |
| Synthetic behavioral features | **FIXED** | Now from REAL cs-training.csv DPD/utilization |
| Model memorizing demographics | **FIXED** | Behavioral swing 22x > demographic swing |
| Demographics dominating SHAP | **FIXED** | 89% behavioral, 11% demographic importance |
| Random number generation for behavioral | **FIXED** | 0/28 features use pure random |

### 10.2 Remaining Limitations (see Section 16 for full flaw audit)

| Issue | Severity | Status |
|-------|----------|--------|
| **API uses OLD 30-feature circular model, NOT v3** | 🔴 CRITICAL | scorer.py loads `pdr_ntc_model.pkl` instead of `ntc_credit_model.pkl` |
| **feature_engine.py outputs 32 features, v3 needs 49** | 🔴 CRITICAL | 25 features missing at inference |
| **middleman_scorer.py hardcodes PD=0.25** | 🔴 CRITICAL | Real extractors exist but aren't wired |
| **MSME model AUC=0.59 (random)** | 🔴 CRITICAL | Needs full rebuild |
| **v3 model wrapper (CalibratedClassifierCV) breaks SHAP** | 🟠 HIGH | `get_booster()` doesn't work |
| **Grade thresholds differ between scorer.py and tests** | 🟡 MEDIUM | scorer: 0.05/0.15/0.30/0.50, test: 0.35/0.55 |
| Demographics from Home Credit (not Indian) | 🟡 MEDIUM | Need Indian demographic dataset |
| Setu API keys hardcoded in main.py | 🟠 HIGH | Visible in GitHub repo |
| 393MB+ CSV files committed to git | 🟡 MEDIUM | Should use .gitignore or LFS |

---

## 11. WHAT HAS BEEN BUILT (CHRONOLOGICAL)

### Phase 1: Core Pipeline (Mar 19)
- 5-file inference pipeline: feature_engine → pre_layer → scorer → main → verify
- 44-feature extractor, 3-tier rule engine, FastAPI backend

### Phase 2: Frontend (Mar 19)
- React + Vite SPA with 3 screens (landing, user select, results)

### Phase 3: AA Integration (Mar 20)
- 6 AA simulation routes + real Setu sandbox integration

### Phase 4: Model Training Fixes (Mar 20-21)
- Fixed data leakage, overlapping distributions, archetype-based split
- Added income stability/seasonality features
- Fixed pre-layer edge cases (NRI, seasonal)
- AUC reached 0.94 (but was circular — inflated)

### Phase 5: Middleman Path (Mar 23)
- 5 simulators, 5 extractors, orchestrator, 4 demo profiles all passing

### Phase 6: Circularity Fix (Mar 23) ★
1. **Diagnosed circularity:** behavioral features = f(demo_risk), TARGET = f(behavioral) = f(f(demographics))
2. **Attempt v2 (noise):** Added independent Beta(2.5,2.5) noise → reduced correlation but still synthetic
3. **Discovered cs-training.csv:** 150K real credit records with REAL DPD, utilization, debt ratio, TARGET
4. **Attempt v3 (real data):** Mapped cs-training behavioral to our features, randomly paired Home Credit demographics
5. **Source audit:** Verified 0/28 behavioral features use pure random generation
6. **Removed all rng.normal() calls** from behavioral features
7. **Fixed business_vintage_months** from age (demographic) to OpenCreditLines (behavioral)
8. **Results:** TARGET↔demo corr: 0.52→0.08, demo-only AUC: 0.83→0.64, behavioral lift: +0.07→+0.21

### Phase 7: Validation (Mar 23-24)
- Memorization test: PASS (behavioral 22x more influential than demographics)
- Contradiction test: PASS (bad behavior + good demographics = higher risk)
- Real data test: MyTransaction.csv → 63.5% → REJECT (correct)
- Feature importance: 89% behavioral, 0 demographics in top 10

### Phase 8: Pre-Layer Hardening + Fraud Analysis (Mar 24) ★
1. Ran all 5 demo users through full pipeline → found NTC_003 (fraud) was being APPROVED (24%)
2. Found seasonal farmer was being HARD REJECTED for min_bal violations
3. Found P2P circular with <3 bounces was passing through to model
4. Found zero-signal empty accounts were being APPROVED
5. Added 10 new rules: balance inflation detection, seasonal exemption, P2P at any bounce, zero-signal catch, declining business, chronic late payer, gig worker, seasonal farmer min_bal
6. All 5 demo users + 8 edge cases now pass correctly
7. Analyzed CC fraud dataset (`synthetic_fraud_dataset.csv`) → REJECTED as unusable (100% synthetic, 32% fraud rate, uniform distributions, wrong domain)
8. Decided against separate fraud ML model — rule-based pre-layer is more defensible

### Phase 9: Full System Audit (Mar 25) ★★
1. Discovered **API uses OLD circular 30-feature model** — `scorer.py` loads `pdr_ntc_model.pkl`, not the fixed `ntc_credit_model.pkl`
2. Found **feature_engine.py outputs 32 features, v3 model needs 49** — 25 features missing at inference, 7 extra unused
3. Found **middleman_scorer.py returns hardcoded PD=0.25** — real extractors exist in `ntc_model/middleman/` but aren't wired
4. Found **v3 model wrapped in CalibratedClassifierCV** — breaks `get_booster()` and SHAP TreeExplainer
5. Found **3 different compute_features() implementations** that are out of sync
6. Found **grade thresholds differ** between scorer.py and test scripts
7. Found **Setu API credentials hardcoded** in main.py (visible in GitHub)
8. Documented all 22 flaws across 7 categories (see Section 16)

---

## 12. REMAINING FOR HACKATHON

```
CURRENT STATUS (as of Phase 9 audit)
──────────────────────────────────────────
NTC model v3:     TRAINED (AUC=0.85), BUT NOT WIRED TO API ← CRITICAL
Pre-layer:        WORKING, 5/5 demo + 8/8 edge cases, 20 rules
Middleman path:   Extractors BUILT, but scorer returns hardcoded PD=0.25
Frontend:         WORKING, 3 screens
FastAPI:          15 endpoints, uses WRONG model

CRITICAL FIXES (must do before demo)
──────────────────────────────────────────
1. Wire v3 model to scorer.py (replace pdr_ntc_model.pkl → ntc_credit_model.pkl + preprocessor)
2. Update feature_engine.py to output all 49 features the v3 model expects
3. Handle CalibratedClassifierCV wrapper for SHAP compatibility
4. Align grade thresholds across scorer.py, tests, and pre-layer
5. Wire real middleman extractors into middleman_scorer.py (replace PD=0.25)

IMPORTANT FIXES
──────────────────────────────────────────
6. Fix MSME model (AUC=0.59 → needs rebuild)
7. Move Setu credentials to environment variables only
8. Delete stale files (old models, debug outputs, 393MB CSVs)

NICE TO HAVE
──────────────────────────────────────────
9. Integration test: API call → frontend display
10. Update demo_users.json with all 49 features
11. Pitch preparation
```

---

## 13. HOW TO RUN

```bash
# Backend
cd alternative_credit_scoring
pip install fastapi uvicorn pandas numpy scikit-learn xgboost shap joblib python-dateutil
python main.py  # API at localhost:8000

# NTC Model Training (v3 — real data)
cd ntc_model
python build_ntc_training_v3.py  # Generate training data from cs-training + Home Credit
python main.py                    # Train XGBoost → evaluate → save
python circularity_diagnostic.py  # Verify circularity is broken
python honest_assessment.py       # Full assessment (memorization, real data, importance)

# Middleman Path
cd ntc_model
python middleman/test_middleman_path.py  # 4/4 profiles pass

# Frontend
cd pdr-frontend
npm install && npm run dev  # localhost:5173
```

---

## 14. CC FRAUD DATASET — ANALYZED AND REJECTED

Dataset: `cc dataset/synthetic_fraud_dataset.csv` (50K rows, 21 cols)

**Verdict: DO NOT USE.** Here's why:

| Red Flag | Evidence |
|----------|----------|
| Filename says "synthetic" | `synthetic_fraud_dataset.csv` |
| 32% fraud rate | Real-world is 0.1-0.5% (200x too high) |
| Uniform distributions | Risk_Score kurtosis=-1.203, Balance=-1.210, Card_Age=-1.203 (all `np.random.uniform()`) |
| No feature separation | ALL categories (POS/ATM/Mobile/Mumbai/NY) have identical ~32% fraud rates |
| Only 2 features with signal | `Failed_Transaction_Count_7d` (corr=0.50) and `Risk_Score` (corr=0.39, but this is a leak) |
| Wrong domain | Credit cards in London/NY/Sydney, not Indian UPI/MSME |

Our pre-layer rule engine (20 rules, RBI/CIBIL/NABARD sourced) is a stronger, more defensible fraud detection approach.

---

## 15. QUESTIONS FOR THE AI

Given this complete context and the 22 flaws documented in Section 16:

1. **Fix the model wiring:** How should we wire `ntc_credit_model.pkl` (CalibratedClassifierCV, 49 features + preprocessor) into `scorer.py` while maintaining SHAP compatibility?

2. **Fix feature_engine.py:** The root feature_engine outputs 32 features, the v3 model needs 49. Which 25 missing features can be derived from bank transactions, and which should be removed from the model entirely?

3. **Fix middleman_scorer.py:** Replace the hardcoded PD=0.25 with the real extractors in `ntc_model/middleman/`. How should the confidence-adjusted thresholds work?

4. **How should we rebuild the MSME model?** We have loan_dataset_20000.csv. Should we use the same approach as v3 (real behavioral + paired demographics)?

5. **What's the best use of remaining time (~6 days)?** Given the 5 critical fixes needed, what order maximizes hackathon demo quality?

6. **How to handle CalibratedClassifierCV for SHAP?** The v3 model wraps XGBoost in Platt scaling. SHAP TreeExplainer needs `get_booster()` which doesn't work on the wrapper.

---

## 16. COMPLETE FLAW AUDIT (22 FLAWS)

### 🔴 CRITICAL (5 flaws)

**FLAW C1 — API USES OLD CIRCULAR MODEL**
- `scorer.py` lines 34-35 load `pdr_ntc_model.pkl` (30 features, OLD circular)
- Should load `ntc_model/models/ntc_credit_model.pkl` (49 features, v3 fixed)
- ALL circularity fixes, memorization tests, and validation are NOT deployed
- The production API still has TARGET↔demo correlation of 0.52

**FLAW C2 — FEATURE ENGINE MISMATCH (32 vs 49 features)**
- Root `feature_engine.py` outputs 32 features
- v3 model expects 49 features
- 25 features MISSING at inference (all default to 0.0 via fillna):
  `applicant_age_years, employment_vintage_days, income_stability_score, income_seasonality_flag, night_transaction_ratio, weekend_spending_ratio, payment_diversity_score, device_consistency_score, geographic_risk_score, region_risk_tier, region_city_risk_score, family_burden_ratio, income_type_risk_score, family_status_stability_score, contactability_score, address_stability_years, id_document_age_years, owns_property, owns_car, car_age_years, has_email_flag, address_work_mismatch, neighbourhood_default_rate_30, neighbourhood_default_rate_60, employment_to_age_ratio`
- 7 features EXTRA in feature_engine (not used by v3 model):
  `operating_cashflow_ratio, avg_invoice_payment_delay, round_number_spike_ratio, repeat_customer_revenue_pct, vendor_payment_discipline, benford_anomaly_score, monthly_income`

**FLAW C3 — MIDDLEMAN SCORER HARDCODED**
- `middleman_scorer.py` line 38: `probability_default = 0.25`
- Always returns same PD regardless of input
- Real extractors exist in `ntc_model/middleman/` but aren't connected

**FLAW C4 — MSME MODEL BROKEN**
- `pdr_msme_model.pkl` has AUC=0.59 (barely above random 0.50)
- Any MSME user gets essentially random grades

**FLAW C5 — DUPLICATE FEATURE ENGINES**
- Root `feature_engine.py`: 32 features, `compute_features(transactions, profile, gst_data)`
- `ntc_model/feature_engine.py`: 552 lines, `extract_features(statement)` — completely different API
- `generate_realistic_training_data.py`: embedded `compute_features()` copy
- None of them produce the 49 features the v3 model needs

### 🟠 HIGH (4 flaws)

**FLAW H1 — v3 MODEL WRAPPER BREAKS SHAP**
- v3 model type is `CalibratedClassifierCV`, not `XGBClassifier`
- `model.get_booster()` fails → SHAP TreeExplainer can't initialize
- `scorer.py` line 42 would crash: `ntc_model.get_booster().feature_names`
- Fix: access inner estimator via `model.estimators_[0].estimator`

**FLAW H2 — NO PREPROCESSOR IN SCORER**
- v3 model uses `ntc_preprocessor.pkl` (ColumnTransformer) for scaling
- `scorer.py` feeds raw values directly to model — no scaling step
- Wiring v3 model requires adding preprocessor.transform() before predict

**FLAW H3 — PRE-LAYER CHECKS FEATURES THAT DON'T EXIST**
- Pre-layer checks `income_stability_score`, `income_seasonality_flag`, `night_transaction_ratio`
- Root `feature_engine.py` never computes these
- At inference, these use `.get(name, 0)` defaults → rules may not fire correctly

**FLAW H4 — SETU CREDENTIALS HARDCODED**
- `main.py` lines 75-77: API keys visible in source
- Pushed to public GitHub repo

### 🟡 MEDIUM (8 flaws)

**FLAW M1 — SCORER HARD-OVERRIDES ARE DEAD CODE**
- `scorer.py` lines 222-225: overrides `pd_score` for p2p_circular and identity_mismatch
- Pre-layer now catches both cases BEFORE scorer runs → overrides never execute

**FLAW M2 — GRADE THRESHOLDS INCONSISTENT**
- `scorer.py`: A<0.05, B<0.15, C<0.30, D<0.50, E>=0.50
- `test_full_pipeline.py`: APPROVE<0.35, REVIEW<0.55, REJECT>=0.55
- Demo users tested with different thresholds than production

**FLAW M3 — NTC_002 SEVERITY MISMATCH**
- Expected: C/MANUAL REVIEW (cash-dependent worker, needs human review)
- Actual: E/REJECTED (min_bal=5 triggers hard rejection)
- Pre-layer is more aggressive than intended for cash-dependent workers

**FLAW M4 — STALE TRAINING SCRIPTS**
- `generate_realistic_training_data.py` generates OLD 30-feature data
- `train.py` trains OLD model
- Both superseded by `build_ntc_training_v3.py` + `ntc_model/main.py`

**FLAW M5 — RADAR CHART DATA STATIC**
- `demo_users.json` has pre-computed radar scores that don't update with model changes

**FLAW M6 — DEMO USERS HAVE 12 FEATURES, MODEL NEEDS 49**
- Demo users in `demo_users.json` only specify ~12 features in `ntc_features`
- Remaining 37+ features default to 0 at scoring time

**FLAW M7 — 393MB+ FILES IN GIT**
- `accepted_2007_to_2018Q4.csv.gz` (374MB), `application_train.csv` (166MB)
- Should be gitignored or in LFS

**FLAW M8 — ~30 DEBUG OUTPUT FILES**
- `out_demo_v1.txt` through `out_demo_v13.txt`, `out_build_v1.txt` through `out_build_v5.txt`, etc.
- Development artifacts adding noise to repo

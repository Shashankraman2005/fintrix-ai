# FintrixAi — AI-Powered Alternate Credit Scoring

> B2B SaaS platform for scoring "credit-invisible" borrowers in India — MSMEs and New-to-Credit (NTC) individuals — using alternative data, ML, and explainable AI.

**Built for Barclays Hack-O-Hire 2026** | Selected from 15,000+ teams across India

---

## The Problem

Over 400 million Indians lack a formal credit history. Traditional scoring models (CIBIL, Experian) rely on repayment data that simply doesn't exist for:

- **MSMEs** — Small businesses operating primarily in cash, with no digital paper trail.
- **NTC Individuals** — First-time borrowers with zero bureau records.

Lenders either reject these applicants outright or price risk too high, locking out a massive creditworthy population.

## Our Solution

FintrixAi is a **4-layer trust-gated pipeline** that ingests alternative data (UPI transactions, GST filings, utility bills, bank statements) and produces a credit score with full regulatory explainability.

```
┌─────────────────────────────────────────────────────┐
│  Layer 1 — Data Ingestion (AA-Ready)                │
│  Digitally signed, RBI-compliant data via Account   │
│  Aggregator framework                               │
├─────────────────────────────────────────────────────┤
│  Layer 2 — Fraud Detection                          │
│  Graph-based circular loop detection + Benford's    │
│  Law anomaly flagging on transaction ledgers        │
├─────────────────────────────────────────────────────┤
│  Layer 3 — Credit Scoring Engine                    │
│  XGBoost + Bayesian modeling on 53 engineered       │
│  features (Test AUC: 0.7433)                        │
├─────────────────────────────────────────────────────┤
│  Layer 4 — Explainability (XAI)                     │
│  SHAP-based reason codes for every decision,        │
│  enabling regulatory transparency                   │
└─────────────────────────────────────────────────────┘
```

## Key Features

- **Account Aggregator Integration** — Ingestion layer designed for India's AA framework with digitally signed consent-based data flow.
- **Dual Assessment Paths** — Separate 5-step evaluation flows for MSMEs and NTC individuals, each with tailored feature sets.
- **Fraud Detection** — Graph theory for detecting circular transaction loops; Benford's Law for flagging anomalous ledger entries.
- **Explainable Decisions** — Every score ships with SHAP-generated "reason codes" that satisfy RBI audit requirements.
- **Surrogate Data Pipeline** — For cash-only MSMEs with no digital footprint, we ingest proxy signals (rent, utilities, trade references).

## Tech Stack

| Layer | Stack |
|---|---|
| ML / Scoring | XGBoost, Scikit-learn, SHAP, Pandas, NumPy |
| Backend | FastAPI (Python) |
| Frontend | Streamlit |
| Fraud Detection | NetworkX (graph analysis), custom Benford's Law module |
| Data | Synthetic dataset — 53 engineered features |
| Explainability | SHAP (TreeExplainer) |

## Model Performance

| Metric | MSME Model |
|---|---|
| Test AUC | 0.7433 |
| Scoring Method | XGBoost + Bayesian prior |
| Features | 53 (engineered from alt-data signals) |
| Explainability | SHAP reason codes per prediction |

## Demo Profiles

The platform includes 5 pre-built demo profiles to showcase different borrower archetypes:

| Profile | Type | Scenario |
|---|---|---|
| Priya Venkataraman | NTC | Salaried first-time borrower |
| Ramesh Gowda | MSME | Small retailer, cash-heavy |
| Deepak Malhotra | MSME | Established trader, partial digital trail |
| Sukhwinder Singh | MSME | Agricultural supplier, seasonal income |
| Mohammed Farouk | NTC | Gig worker, no bureau history |

## Project Structure

```
pdr/
├── backend/              # FastAPI server
├── frontend/             # Streamlit UI
├── ml/
│   ├── notebooks/        # Training notebooks (XGBoost, feature engineering)
│   ├── models/           # Serialized model artifacts
│   └── shap/             # Explainability module
├── fraud/
│   ├── graph_detection/  # Circular loop detection (NetworkX)
│   └── benfords/         # Benford's Law anomaly flagging
├── data/
│   └── synthetic/        # Generated dataset (53 features)
├── demo/                 # Demo profiles and AA flow simulation
└── docs/                 # Architecture diagrams, pitch deck
```

## Getting Started

```bash
# Clone
git clone https://github.com/<your-username>/pdr.git
cd pdr

# Install dependencies
pip install -r requirements.txt

# Run backend
uvicorn backend.main:app --reload

# Run frontend (separate terminal)
streamlit run frontend/app.py
```

## Architecture

```
                    ┌──────────────┐
                    │   Lender UI  │
                    │  (Streamlit) │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   FastAPI    │
                    │   Backend    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
      ┌───────▼──┐  ┌─────▼─────┐  ┌──▼────────┐
      │  AA Data │  │   Fraud   │  │  Scoring  │
      │ Ingestion│  │ Detection │  │  Engine   │
      └──────────┘  └───────────┘  └─────┬─────┘
                                         │
                                   ┌─────▼─────┐
                                   │   SHAP    │
                                   │  Reason   │
                                   │  Codes    │
                                   └───────────┘
```

## Team

| Member | Role |
|---|---|
| **Sumit** | ML Pipeline, XGBoost Training, Demo Profiles, Presentation |
| **Rayirth Misra** | Backend Architecture, Fraud Detection, System Design |
| **Tvisha Lakdawala** | Frontend, UX Design, Assessment Flows |
| **Lubdhak Mandal** | Data Engineering, Feature Engineering |
| **Kaavya Gupta** | Research, Explainability Module, Documentation |

## License

MIT

---

*Built at Barclays Hack-O-Hire 2026*

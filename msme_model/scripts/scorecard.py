"""
MSME Credit Scorecard
======================
Converts XGBoost default probability into a 300–900 credit score.
Produces a full breakdown by the 4 risk categories so a loan officer
can see not just the score but WHY it is that score.

Category Weights (from PDR Risk Framework):
  Operational Stability  50%  →  OCR, volatility, growth, seasonality, vintage
  Network & Compliance   25%  →  GST filing, concentration, vendor payment, repeat
  Liquidity              15%  →  invoice payment delay
  Forensic/Alternative   10%  →  GST-bank variance, turnover spike

Score Bands:
  750 – 900   GREEN   →  Approve
  650 – 749   AMBER   →  Approve with conditions
  550 – 649   YELLOW  →  Manual review
  300 – 549   RED     →  Decline

Run:
  python scripts/scorecard.py                        (scores all test records)
  python scripts/scorecard.py --single               (interactive single business)

Output:
  reports/scorecard_results.csv
  reports/scorecard_report.png
"""

import os
import sys
import pickle
import argparse
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR    = os.path.join(BASE_DIR, "data")
MODEL_DIR   = os.path.join(BASE_DIR, "models")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# ── Score band definitions ────────────────────────────────────
BANDS = [
    (637, 666, "GREEN",  "Approve",                "#2ecc71"),
    (620, 636, "AMBER",  "Approve with Conditions", "#f39c12"),
    (598, 619, "YELLOW", "Manual Review",           "#f1c40f"),
    (550, 597, "RED",    "Decline",                 "#e74c3c"),
]

SCORE_MIN = 300
SCORE_MAX = 900

# ── Category weight framework ─────────────────────────────────
# These reflect your PDR Risk Framework exactly.
# Each category has features + their sub-weights (must sum to 1.0 per category).

CATEGORIES = {
    "Operational Stability": {
        "weight": 0.50,
        "color":  "#3498db",
        "features": {
            # feature: (direction, lo, hi, sub_weight)
            # direction: -1 = higher value is BETTER (lowers risk)
            #             1 = higher value is WORSE  (raises risk)
            "operating_cashflow_ratio":  (-1, 0.45, 2.20, 0.45),
            "cashflow_volatility":       ( 1, 0.02, 0.93, 0.30),
            "revenue_growth_trend":      (-1, -0.19, 0.28, 0.14),
            "revenue_seasonality_index": ( 1, 0.01, 0.98, 0.06),
            "business_vintage_months":   (-1, 3.0, 210.0, 0.05),
        }
    },
    "Network & Compliance": {
        "weight": 0.25,
        "color":  "#9b59b6",
        "features": {
            "gst_filing_consistency_score": (-1, 0, 12,   0.35),
            "customer_concentration_ratio": ( 1, 0.02, 1.0, 0.28),
            "vendor_payment_discipline":    ( 1, 0.0, 75.2, 0.22),
            "repeat_customer_revenue_pct":  (-1, 0.0, 0.98, 0.15),
        }
    },
    "Liquidity": {
        "weight": 0.15,
        "color":  "#1abc9c",
        "features": {
            "avg_invoice_payment_delay": (1, 3.0, 143.9, 1.00),
        }
    },
    "Forensic / Alternative": {
        "weight": 0.10,
        "color":  "#e74c3c",
        "features": {
            "gst_to_bank_variance":      (1, 0.0, 0.62, 0.70),
            "turnover_inflation_spike":  (1, 0.0, 1.0,  0.30),
        }
    },
}

# ── Core scoring functions ────────────────────────────────────

def probability_to_score(prob: float) -> float:
    """
    Convert default probability to 300–900 score.
    Higher probability → lower score.
    Uses log-odds scaling (standard in credit scoring).
    """
    prob = np.clip(prob, 0.001, 0.999)
    log_odds = np.log(prob / (1 - prob))
    # Map log_odds range [-6, +6] → score range [900, 300]
    score = SCORE_MAX + (SCORE_MIN - SCORE_MAX) * (log_odds + 6) / 12
    return float(np.clip(score, SCORE_MIN, SCORE_MAX))


def get_band(score: float) -> dict:
    for lo, hi, band, action, color in BANDS:
        if lo <= score <= hi:
            return {"band": band, "action": action, "color": color}
    return {"band": "RED", "action": "Decline", "color": "#e74c3c"}


def score_category(row: pd.Series, cat_name: str) -> dict:
    """
    Score a single category for one business.
    Returns raw score (0–100) and per-feature contributions.
    """
    cat = CATEGORIES[cat_name]
    cat_score = 0.0
    feature_scores = {}

    for feat, (direction, lo, hi, sub_w) in cat["features"].items():
        val = float(row.get(feat, np.nan))
        if np.isnan(val):
            # Missing feature — assume worst case
            norm_val = 1.0 if direction == 1 else 0.0
        else:
            norm_val = (val - lo) / (hi - lo + 1e-9)
            norm_val = float(np.clip(norm_val, 0.0, 1.0))

        # Risk contribution: direction=1 means higher norm = higher risk
        if direction == 1:
            risk = norm_val          # 0 = best, 1 = worst
        else:
            risk = 1.0 - norm_val   # invert: higher value = lower risk

        feature_scores[feat] = {
            "value":       val,
            "risk_pct":    round(risk * 100, 1),
            "contribution": round(risk * sub_w * 100, 2),
        }
        cat_score += risk * sub_w

    return {
        "category_risk": round(cat_score * 100, 1),   # 0=best 100=worst
        "features": feature_scores,
    }


def score_business(row: pd.Series, model, scaler, feature_cols: list) -> dict:
    """
    Full scorecard for a single business row.
    Returns score, band, category breakdown, and model probability.
    """
    # ── Add interaction features ──────────────────────────────
    row = row.copy()
    row["stress_composite"]    = row["cashflow_volatility"] / (row["operating_cashflow_ratio"] + 1e-9)
    row["gst_risk_score"]      = row["gst_to_bank_variance"] * (12 - row["gst_filing_consistency_score"])
    row["wc_pressure"]         = row["avg_invoice_payment_delay"] * row["customer_concentration_ratio"]
    row["liquidity_fragility"] = row["revenue_seasonality_index"] / (row["operating_cashflow_ratio"] + 1e-9)

    # ── One-hot encode business_type ──────────────────────────
    biz_type = row.get("business_type", "unknown")
    for bt in ["agri_seasonal", "manufacturer", "retailer_kirana", "service_provider"]:
        row[f"business_type_{bt}"] = 1 if biz_type == bt else 0

    # ── Build feature vector ──────────────────────────────────
    BOOL_COLS = ["turnover_inflation_spike"] + [c for c in feature_cols if "business_type_" in c]
    NUM_COLS  = [c for c in feature_cols if c not in BOOL_COLS]

    X = pd.DataFrame([row])[feature_cols].fillna(0)
    X[NUM_COLS] = scaler.transform(X[NUM_COLS])

    # ── Model probability ─────────────────────────────────────
    prob = float(model.predict_proba(X)[0, 1])

    # ── Convert to score ──────────────────────────────────────
    score = probability_to_score(prob)
    band  = get_band(score)

    # ── Category breakdown ────────────────────────────────────
    category_results = {}
    weighted_risk = 0.0
    for cat_name, cat_cfg in CATEGORIES.items():
        result = score_category(row, cat_name)
        category_results[cat_name] = result
        weighted_risk += result["category_risk"] * cat_cfg["weight"]

    return {
        "score":            round(score),
        "band":             band["band"],
        "action":           band["action"],
        "band_color":       band["color"],
        "default_prob":     round(prob * 100, 1),
        "weighted_risk":    round(weighted_risk, 1),
        "categories":       category_results,
        "business_type":    biz_type,
    }


# ── Batch scoring ─────────────────────────────────────────────

def score_all(df: pd.DataFrame, model, scaler, feature_cols: list) -> pd.DataFrame:
    results = []
    for _, row in df.iterrows():
        r = score_business(row, model, scaler, feature_cols)
        results.append({
            "business_id":               row.get("business_id", "N/A"),
            "business_type":             r["business_type"],
            "credit_score":              r["score"],
            "band":                      r["band"],
            "action":                    r["action"],
            "default_probability_pct":   r["default_prob"],
            "operational_risk":          r["categories"]["Operational Stability"]["category_risk"],
            "network_risk":              r["categories"]["Network & Compliance"]["category_risk"],
            "liquidity_risk":            r["categories"]["Liquidity"]["category_risk"],
            "forensic_risk":             r["categories"]["Forensic / Alternative"]["category_risk"],
            "actual_default":            int(row.get("default", -1)),
        })
    return pd.DataFrame(results)


# ── Scorecard report chart ────────────────────────────────────

def plot_scorecard_report(results_df: pd.DataFrame):
    BG, PANEL, BORDER = "#0d1117", "#161b22", "#30363d"
    WHITE, MUTED      = "#e6edf3", "#8b949e"

    fig = plt.figure(figsize=(24, 28), facecolor=BG)
    fig.suptitle("MSME Credit Scorecard — Portfolio Report",
                 fontsize=20, fontweight="bold", color=WHITE,
                 y=0.98, family="monospace")
    outer = gridspec.GridSpec(4, 1, figure=fig, hspace=0.45,
                              top=0.965, bottom=0.03, left=0.05, right=0.97)

    def style_ax(ax, title=None):
        ax.set_facecolor(PANEL)
        ax.tick_params(colors=MUTED, labelsize=9)
        for s in ax.spines.values(): s.set_edgecolor(BORDER)
        if title:
            ax.set_title(title, color=WHITE, fontsize=11,
                         pad=10, family="monospace")

    BAND_COLORS = {
        "GREEN":  "#2ecc71",
        "AMBER":  "#f39c12",
        "YELLOW": "#f1c40f",
        "RED":    "#e74c3c",
    }

    # ── Row 1: Score distribution + Band breakdown ────────────
    r1 = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=outer[0], wspace=0.35)

    # Score histogram
    ax = fig.add_subplot(r1[0])
    style_ax(ax, "① Credit Score Distribution")
    for lo, hi, band, action, color in BANDS:
        mask = (results_df["credit_score"] >= lo) & (results_df["credit_score"] <= hi)
        ax.hist(results_df[mask]["credit_score"], bins=20,
                color=color, alpha=0.80, label=f"{band} ({mask.sum()})", linewidth=0)
    ax.axvline(750, color=WHITE, lw=1, linestyle="--", alpha=0.5)
    ax.axvline(650, color=WHITE, lw=1, linestyle="--", alpha=0.5)
    ax.axvline(550, color=WHITE, lw=1, linestyle="--", alpha=0.5)
    ax.set_xlabel("Credit Score", color=MUTED, fontsize=9)
    ax.set_ylabel("Count", color=MUTED, fontsize=9)
    ax.legend(fontsize=8, facecolor="#1c2128", labelcolor=WHITE)

    # Band pie
    ax = fig.add_subplot(r1[1])
    ax.set_facecolor(PANEL)
    style_ax(ax, "② Portfolio Band Distribution")
    band_counts = results_df["band"].value_counts().reindex(
        ["GREEN", "AMBER", "YELLOW", "RED"], fill_value=0)
    ax.pie(band_counts.values,
           labels=[f"{b}\n({n})" for b, n in zip(band_counts.index, band_counts.values)],
           colors=[BAND_COLORS[b] for b in band_counts.index],
           autopct="%1.1f%%",
           textprops={"color": WHITE, "fontsize": 9},
           wedgeprops={"edgecolor": BG, "linewidth": 2})

    # ── Row 2: Default rate by band + score by business type ──
    r2 = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=outer[1], wspace=0.35)

    # Default rate by band
    ax = fig.add_subplot(r2[0])
    style_ax(ax, "③ Actual Default Rate by Score Band")
    valid = results_df[results_df["actual_default"] >= 0]
    band_default = valid.groupby("band")["actual_default"].mean().reindex(
        ["GREEN", "AMBER", "YELLOW", "RED"], fill_value=0)
    bars = ax.bar(band_default.index, band_default.values,
                  color=[BAND_COLORS[b] for b in band_default.index],
                  width=0.5, edgecolor=BG)
    for bar, val in zip(bars, band_default.values):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.008,
                f"{val:.1%}", ha="center", fontsize=10,
                color=WHITE, fontweight="bold")
    ax.set_ylabel("Default Rate", color=MUTED, fontsize=9)
    ax.set_ylim(0, min(1.0, band_default.max() + 0.15))

    # Score by business type box plot
    ax = fig.add_subplot(r2[1])
    style_ax(ax, "④ Credit Score by Business Type")
    TYPE_COLORS = {
        "agri_seasonal":    "#f1c40f",
        "manufacturer":     "#3498db",
        "service_provider": "#2ecc71",
        "retailer_kirana":  "#e74c3c",
    }
    types = ["agri_seasonal", "manufacturer", "service_provider", "retailer_kirana"]
    data  = [results_df[results_df["business_type"] == t]["credit_score"].values for t in types]
    bp = ax.boxplot(data, patch_artist=True,
                    medianprops={"color": WHITE, "linewidth": 2})
    for patch, t in zip(bp["boxes"], types):
        patch.set_facecolor(TYPE_COLORS[t]); patch.set_alpha(0.75)
    for el in ["whiskers", "caps", "fliers"]:
        for item in bp[el]: item.set_color(MUTED)
    labels = ["Agri", "Mfg", "Service", "Retail"]
    ax.set_xticklabels(labels, color=WHITE, fontsize=9)
    ax.set_ylabel("Credit Score", color=MUTED, fontsize=9)
    for lo, _, band, _, _ in BANDS[:-1]:
        ax.axhline(lo, color=MUTED, linestyle="--", lw=0.8, alpha=0.5)

    # ── Row 3: Category risk heatmap ──────────────────────────
    r3 = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=outer[2])
    ax = fig.add_subplot(r3[0])
    style_ax(ax, "⑤ Average Category Risk by Business Type & Band")

    cat_cols = ["operational_risk", "network_risk", "liquidity_risk", "forensic_risk"]
    cat_labels = ["Operational\n(50%)", "Network\n(25%)", "Liquidity\n(15%)", "Forensic\n(10%)"]
    pivot = results_df.groupby("business_type")[cat_cols].mean().reindex(types)

    import matplotlib.colors as mcolors
    cmap = plt.cm.RdYlGn_r
    im = ax.imshow(pivot.values, cmap=cmap, aspect="auto", vmin=0, vmax=80)
    ax.set_xticks(range(4)); ax.set_xticklabels(cat_labels, color=WHITE, fontsize=9)
    ax.set_yticks(range(4)); ax.set_yticklabels(
        ["Agri/Seasonal", "Manufacturer", "Service Provider", "Retailer/Kirana"],
        color=WHITE, fontsize=9)
    for i in range(4):
        for j in range(4):
            val = pivot.values[i, j]
            ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                    fontsize=11, color="black" if val < 60 else "white",
                    fontweight="bold")
    plt.colorbar(im, ax=ax, shrink=0.6, label="Risk Score (0=best 100=worst)")

    # ── Row 4: Score vs Default Probability scatter ───────────
    r4 = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=outer[3], wspace=0.35)

    ax = fig.add_subplot(r4[0])
    style_ax(ax, "⑥ Score vs Default Probability")
    sc = ax.scatter(results_df["credit_score"],
                    results_df["default_probability_pct"],
                    c=results_df["actual_default"],
                    cmap="RdYlGn_r", alpha=0.35, s=12)
    for lo, _, _, _, _ in BANDS[:-1]:
        ax.axvline(lo, color=MUTED, linestyle="--", lw=0.8, alpha=0.5)
    ax.set_xlabel("Credit Score", color=MUTED, fontsize=9)
    ax.set_ylabel("Default Probability (%)", color=MUTED, fontsize=9)
    plt.colorbar(sc, ax=ax, shrink=0.7, label="Actual Default")

    # Summary stats table
    ax = fig.add_subplot(r4[1])
    ax.axis("off"); ax.set_facecolor(PANEL)
    ax.text(0.01, 0.97, "⑦  Portfolio Summary",
            fontsize=12, color=MUTED, fontweight="bold",
            transform=ax.transAxes, va="top", family="monospace")

    summary = [
        ("Total Businesses",   f"{len(results_df):,}"),
        ("Mean Credit Score",  f"{results_df['credit_score'].mean():.0f}"),
        ("Median Credit Score",f"{results_df['credit_score'].median():.0f}"),
        ("GREEN (Approve)",    f"{(results_df['band']=='GREEN').sum():,}  "
                               f"({(results_df['band']=='GREEN').mean():.1%})"),
        ("AMBER (Conditional)",f"{(results_df['band']=='AMBER').sum():,}  "
                               f"({(results_df['band']=='AMBER').mean():.1%})"),
        ("YELLOW (Review)",    f"{(results_df['band']=='YELLOW').sum():,}  "
                               f"({(results_df['band']=='YELLOW').mean():.1%})"),
        ("RED (Decline)",      f"{(results_df['band']=='RED').sum():,}  "
                               f"({(results_df['band']=='RED').mean():.1%})"),
        ("Actual Default Rate",f"{results_df[results_df['actual_default']>=0]['actual_default'].mean():.1%}"),
    ]
    for j, (label, value) in enumerate(summary):
        y_ = 0.82 - j * 0.10
        ax.text(0.01, y_, label, fontsize=9,  color=MUTED,
                transform=ax.transAxes, va="top")
        ax.text(0.60, y_, value, fontsize=10, color=WHITE,
                transform=ax.transAxes, va="top", fontweight="bold")

    out = os.path.join(REPORTS_DIR, "scorecard_report.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    print(f"✅ Scorecard report saved → {out}")


# ── Single business interactive scorer ───────────────────────

def score_single(model, scaler, feature_cols):
    print("\n" + "="*55)
    print("  MSME CREDIT SCORECARD — Single Business Scorer")
    print("="*55)

    types = ["agri_seasonal", "manufacturer", "service_provider", "retailer_kirana"]
    print("\nBusiness types: " + " | ".join(f"{i+1}.{t}" for i,t in enumerate(types)))
    t_idx = int(input("Select business type (1-4): ")) - 1
    biz_type = types[t_idx]

    fields = {
        "business_vintage_months":      ("Business vintage (months)", 36),
        "revenue_growth_trend":         ("Revenue growth MoM (e.g. 0.05)", 0.03),
        "revenue_seasonality_index":    ("Revenue seasonality index (0-1)", 0.30),
        "operating_cashflow_ratio":     ("Operating cashflow ratio", 1.10),
        "cashflow_volatility":          ("Cashflow volatility (0-1)", 0.35),
        "avg_invoice_payment_delay":    ("Avg invoice payment delay (days)", 30),
        "customer_concentration_ratio": ("Customer concentration ratio (0-1)", 0.40),
        "repeat_customer_revenue_pct":  ("Repeat customer revenue % (0-1)", 0.50),
        "vendor_payment_discipline":    ("Vendor payment DPD (days)", 15),
        "gst_filing_consistency_score": ("GST filing consistency (0-12)", 7),
        "gst_to_bank_variance":         ("GST to bank variance (0-1)", 0.12),
        "turnover_inflation_spike":     ("Turnover inflation spike (0/1)", 0),
    }

    row = {"business_type": biz_type}
    print(f"\nEnter values for {biz_type} (press Enter to use default):\n")
    for feat, (label, default) in fields.items():
        val = input(f"  {label} [{default}]: ").strip()
        row[feat] = float(val) if val else float(default)

    result = score_business(pd.Series(row), model, scaler, feature_cols)

    print("\n" + "="*55)
    print(f"  CREDIT SCORE  :  {result['score']}")
    print(f"  BAND          :  {result['band']}")
    print(f"  DECISION      :  {result['action']}")
    print(f"  DEFAULT PROB  :  {result['default_prob']}%")
    print("="*55)
    print("\n  CATEGORY BREAKDOWN:\n")
    for cat_name, cat_cfg in CATEGORIES.items():
        cat_result = result["categories"][cat_name]
        risk = cat_result["category_risk"]
        bar  = "█" * int(risk / 5) + "░" * (20 - int(risk / 5))
        print(f"  {cat_name:<26} [{bar}] {risk:.0f}/100  (weight {int(cat_cfg['weight']*100)}%)")
    print()


# ── Main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", action="store_true",
                        help="Score a single business interactively")
    args = parser.parse_args()

    # Load model artifacts
    with open(os.path.join(MODEL_DIR, "xgb_msme.pkl"), "rb") as f:
        model = pickle.load(f)
    with open(os.path.join(DATA_DIR, "scaler.pkl"), "rb") as f:
        scaler = pickle.load(f)
    with open(os.path.join(DATA_DIR, "feature_columns.pkl"), "rb") as f:
        feature_cols = pickle.load(f)

    if args.single:
        score_single(model, scaler, feature_cols)
        return

    # Batch score the test set
    X_test = pd.read_csv(os.path.join(DATA_DIR, "X_test.csv"))
    y_test = pd.read_csv(os.path.join(DATA_DIR, "y_test.csv")).squeeze()
    raw    = pd.read_csv(os.path.join(DATA_DIR, "msme_synthetic.csv"))

    # Reconstruct original (unscaled) test rows for category scoring
    test_idx  = X_test.index
    raw_test  = raw.iloc[test_idx].reset_index(drop=True)
    raw_test["default"] = y_test.values

    print(f"Scoring {len(raw_test)} test businesses...")
    results_df = score_all(raw_test, model, scaler, feature_cols)

    # Save CSV
    out_csv = os.path.join(REPORTS_DIR, "scorecard_results.csv")
    results_df.to_csv(out_csv, index=False)
    print(f"✅ Scorecard results saved → {out_csv}")

    # Print summary
    print(f"\n{'='*55}")
    print(f"  PORTFOLIO SUMMARY")
    print(f"{'='*55}")
    print(f"  Total scored   : {len(results_df)}")
    print(f"  Mean score     : {results_df['credit_score'].mean():.0f}")
    print(f"  Score range    : {results_df['credit_score'].min()} – {results_df['credit_score'].max()}")
    print(f"\n  Band breakdown:")
    for band, color in [("GREEN","✅"), ("AMBER","🟡"), ("YELLOW","⚠️"), ("RED","❌")]:
        n   = (results_df["band"] == band).sum()
        pct = n / len(results_df)
        dr  = results_df[results_df["band"]==band]["actual_default"].mean()
        print(f"  {color} {band:<8} {n:>4} ({pct:.1%})  |  Default rate: {dr:.1%}")

    print(f"\n  Default rate by score band validates model:")
    print(f"  GREEN should be lowest, RED should be highest ↑")

    # Plot report
    plot_scorecard_report(results_df)


if __name__ == "__main__":
    main()

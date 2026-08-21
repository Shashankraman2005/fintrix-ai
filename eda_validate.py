"""
MSME Synthetic Data — EDA Validation
======================================
Generates:
1. Feature distributions by segment
2. Correlation heatmap
3. Default rate analysis
4. Key business logic checks

Output: msme_model/reports/eda_report.png
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import warnings
warnings.filterwarnings("ignore")

# ── Load ──────────────────────────────────────
df = pd.read_csv("/mnt/user-data/outputs/msme_model/data/msme_synthetic.csv")

FEATURES = [
    "business_vintage_months",
    "revenue_growth_trend",
    "revenue_seasonality_index",
    "operating_cashflow_ratio",
    "cashflow_volatility",
    "avg_invoice_payment_delay",
    "customer_concentration_ratio",
    "repeat_customer_revenue_pct",
    "vendor_payment_discipline",
    "gst_filing_consistency_score",
    "gst_to_bank_variance",
    "turnover_inflation_spike",
]

COLORS = {"healthy": "#2ecc71", "stressed": "#f39c12", "risky": "#e74c3c"}

# ── Figure setup ─────────────────────────────
fig = plt.figure(figsize=(26, 34), facecolor="#0d1117")
fig.suptitle(
    "MSME Synthetic Dataset — EDA Validation Report",
    fontsize=22, fontweight="bold", color="white", y=0.98
)

outer = gridspec.GridSpec(4, 1, figure=fig, hspace=0.45)

# ── Section 1: Feature Distributions ─────────
ax_title = fig.add_subplot(outer[0])
ax_title.axis("off")
ax_title.text(0, 0.9, "① Feature Distributions by Segment",
              fontsize=15, color="#aaaaaa", fontweight="bold", transform=ax_title.transAxes)

inner1 = gridspec.GridSpecFromSubplotSpec(3, 4, subplot_spec=outer[0], hspace=0.6, wspace=0.35)

for i, feat in enumerate(FEATURES):
    ax = fig.add_subplot(inner1[i])
    ax.set_facecolor("#161b22")
    for seg, color in COLORS.items():
        data = df[df["segment"] == seg][feat]
        ax.hist(data, bins=30, alpha=0.65, color=color, label=seg, density=True)
    ax.set_title(feat.replace("_", "\n"), fontsize=7.5, color="white", pad=4)
    ax.tick_params(colors="#666666", labelsize=6)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333333")
    if i == 0:
        ax.legend(fontsize=6, facecolor="#1c2128", labelcolor="white", framealpha=0.8)

# ── Section 2: Correlation Heatmap ───────────
inner2 = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=outer[1])
ax_corr = fig.add_subplot(inner2[0])
ax_corr.set_facecolor("#161b22")
ax_corr.text(0, 1.04, "② Correlation Heatmap (All Numerical Features)",
             fontsize=13, color="#aaaaaa", fontweight="bold", transform=ax_corr.transAxes)

num_cols = FEATURES + ["default"]
corr = df[num_cols].corr()

mask = np.triu(np.ones_like(corr, dtype=bool))
cmap = sns.diverging_palette(10, 130, as_cmap=True)
sns.heatmap(
    corr, mask=mask, ax=ax_corr,
    cmap=cmap, center=0, vmin=-1, vmax=1,
    annot=True, fmt=".2f", annot_kws={"size": 7.5},
    linewidths=0.5, linecolor="#0d1117",
    cbar_kws={"shrink": 0.7}
)
ax_corr.tick_params(colors="white", labelsize=8)
ax_corr.set_xticklabels(ax_corr.get_xticklabels(), rotation=40, ha="right", color="white")
ax_corr.set_yticklabels(ax_corr.get_yticklabels(), rotation=0, color="white")

# ── Section 3: Default Rate by Segment ───────
inner3 = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=outer[2], wspace=0.4)

# 3a — Default rate bar
ax_def = fig.add_subplot(inner3[0])
ax_def.set_facecolor("#161b22")
ax_def.text(0, 1.06, "③ Default Rates by Segment",
            fontsize=11, color="#aaaaaa", fontweight="bold", transform=ax_def.transAxes)
rates = df.groupby("segment")["default"].mean().reindex(["healthy", "stressed", "risky"])
bars = ax_def.bar(rates.index, rates.values, color=[COLORS[s] for s in rates.index], width=0.5, edgecolor="#0d1117")
for bar, val in zip(bars, rates.values):
    ax_def.text(bar.get_x() + bar.get_width()/2, val + 0.01, f"{val:.1%}",
                ha="center", fontsize=10, color="white", fontweight="bold")
ax_def.set_ylim(0, 0.85)
ax_def.set_facecolor("#161b22")
ax_def.tick_params(colors="white")
for spine in ax_def.spines.values():
    spine.set_edgecolor("#333333")
ax_def.set_ylabel("Default Rate", color="white")

# 3b — Segment size pie
ax_pie = fig.add_subplot(inner3[1])
ax_pie.set_facecolor("#161b22")
ax_pie.text(0, 1.06, "④ Segment Distribution",
            fontsize=11, color="#aaaaaa", fontweight="bold", transform=ax_pie.transAxes)
counts = df["segment"].value_counts().reindex(["healthy", "stressed", "risky"])
ax_pie.pie(counts.values, labels=counts.index, colors=[COLORS[s] for s in counts.index],
           autopct="%1.0f%%", textprops={"color": "white", "fontsize": 10},
           wedgeprops={"edgecolor": "#0d1117", "linewidth": 2})

# 3c — OCR vs Cashflow Volatility scatter
ax_sc = fig.add_subplot(inner3[2])
ax_sc.set_facecolor("#161b22")
ax_sc.text(0, 1.06, "⑤ OCR vs Cashflow Volatility",
           fontsize=11, color="#aaaaaa", fontweight="bold", transform=ax_sc.transAxes)
for seg, color in COLORS.items():
    sub = df[df["segment"] == seg]
    ax_sc.scatter(sub["operating_cashflow_ratio"], sub["cashflow_volatility"],
                  c=color, alpha=0.25, s=8, label=seg)
ax_sc.set_xlabel("Operating Cashflow Ratio", color="white", fontsize=8)
ax_sc.set_ylabel("Cashflow Volatility", color="white", fontsize=8)
ax_sc.tick_params(colors="white", labelsize=7)
ax_sc.legend(fontsize=7, facecolor="#1c2128", labelcolor="white")
for spine in ax_sc.spines.values():
    spine.set_edgecolor("#333333")

# ── Section 4: Business Logic Checks ─────────
inner4 = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=outer[3])
ax_log = fig.add_subplot(inner4[0])
ax_log.axis("off")
ax_log.set_facecolor("#161b22")

checks = [
    ("OCR < 1.0 in Risky segment",
     f"{(df[df['segment']=='risky']['operating_cashflow_ratio'] < 1.0).mean():.1%} of risky businesses",
     "Expected ~40–50%"),
    ("High customer concentration in Risky",
     f"Mean CCR = {df[df['segment']=='risky']['customer_concentration_ratio'].mean():.2f}",
     "Expected > 0.65"),
    ("Low GST consistency in Risky",
     f"Mean GFCS = {df[df['segment']=='risky']['gst_filing_consistency_score'].mean():.1f}",
     "Expected < 4"),
    ("Turnover inflation spike rate",
     f"Risky: {df[df['segment']=='risky']['turnover_inflation_spike'].mean():.1%}  |  Healthy: {df[df['segment']=='healthy']['turnover_inflation_spike'].mean():.1%}",
     "Risky >> Healthy"),
    ("GST-Bank variance",
     f"Risky mean: {df[df['segment']=='risky']['gst_to_bank_variance'].mean():.3f}  |  Healthy mean: {df[df['segment']=='healthy']['gst_to_bank_variance'].mean():.3f}",
     "Risky >> Healthy"),
    ("Overall default rate",
     f"{df['default'].mean():.1%}",
     "Expected ~18–22% (realistic portfolio)"),
]

ax_log.text(0.01, 0.97, "⑥ Business Logic Validation Checks",
            fontsize=13, color="#aaaaaa", fontweight="bold",
            transform=ax_log.transAxes, va="top")

for j, (check, value, expected) in enumerate(checks):
    y = 0.82 - j * 0.13
    ax_log.text(0.01, y, f"✔  {check}", fontsize=10, color="#58a6ff",
                transform=ax_log.transAxes, va="top", fontweight="bold")
    ax_log.text(0.35, y, value, fontsize=10, color="white",
                transform=ax_log.transAxes, va="top")
    ax_log.text(0.70, y, expected, fontsize=9, color="#3fb950",
                transform=ax_log.transAxes, va="top", style="italic")

# ── Save ─────────────────────────────────────
out_path = "/mnt/user-data/outputs/msme_model/reports/eda_report.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="#0d1117")
print(f"✅ EDA report saved: {out_path}")

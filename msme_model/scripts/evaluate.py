"""
MSME Model — Full Evaluation Report
Run: python scripts/evaluate.py
"""
import os, pickle, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


class PlattCalibratedModel:
    """Required to unpickle the calibrated model saved by train.py."""
    def __init__(self, xgb_model, platt_lr):
        self.xgb_model = xgb_model
        self.platt_lr  = platt_lr

    def predict_proba(self, X):
        raw = self.xgb_model.predict_proba(X)[:, 1].reshape(-1, 1)
        cal = self.platt_lr.predict_proba(raw)[:, 1]
        return np.column_stack([1 - cal, cal])
import matplotlib.gridspec as gridspec
from sklearn.metrics import (
    roc_auc_score, roc_curve, precision_recall_curve,
    average_precision_score, confusion_matrix, classification_report
)
warnings.filterwarnings("ignore")

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR    = os.path.join(BASE_DIR, "data")
MODEL_DIR   = os.path.join(BASE_DIR, "models")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")   # ← already works for you, keep as is
os.makedirs(REPORTS_DIR, exist_ok=True)

X_test = pd.read_csv(os.path.join(DATA_DIR, "X_test.csv"))
y_test = pd.read_csv(os.path.join(DATA_DIR, "y_test.csv")).squeeze()
with open(os.path.join(MODEL_DIR, "xgb_msme.pkl"), "rb") as f: model = pickle.load(f)
fi_df = pd.read_csv(os.path.join(MODEL_DIR, "feature_importance.csv"))

print(f"Test set: {len(X_test)} rows | Default rate: {y_test.mean():.1%}")
y_proba = model.predict_proba(X_test)[:, 1]
y_pred  = (y_proba >= 0.50).astype(int)
auc  = roc_auc_score(y_test, y_proba)
gini = 2 * auc - 1
ap   = average_precision_score(y_test, y_proba)
fpr, tpr, roc_thresh = roc_curve(y_test, y_proba)
ks        = float(max(tpr - fpr))
ks_thresh = float(roc_thresh[np.argmax(tpr - fpr)])

print(f"\n{'='*50}\n  FINAL TEST METRICS\n{'='*50}")
print(f"  AUC-ROC  : {auc:.4f}")
print(f"  Gini     : {gini:.4f}")
print(f"  KS Stat  : {ks:.4f}")
print(f"  Avg Prec : {ap:.4f}")
print(f"\n{classification_report(y_test, y_pred, target_names=['Non-Default','Default'])}")

BG,PANEL,BORDER = "#0d1117","#161b22","#30363d"
WHITE,MUTED     = "#e6edf3","#8b949e"
GREEN,RED,BLUE,YELLOW = "#3fb950","#f85149","#58a6ff","#f1c40f"

def style_ax(ax, title=None):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=MUTED, labelsize=9)
    for s in ax.spines.values(): s.set_edgecolor(BORDER)
    if title: ax.set_title(title, color=WHITE, fontsize=11, pad=10, family="monospace")

fig = plt.figure(figsize=(26, 30), facecolor=BG)
fig.suptitle("MSME Credit Model — Evaluation Report",
             fontsize=20, fontweight="bold", color=WHITE, y=0.98, family="monospace")
outer = gridspec.GridSpec(4, 1, figure=fig, hspace=0.50,
                          top=0.965, bottom=0.03, left=0.05, right=0.97)

r1 = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=outer[0], wspace=0.38)
ax = fig.add_subplot(r1[0]); style_ax(ax, f"① ROC Curve  (AUC={auc:.3f})")
ax.plot(fpr, tpr, color=BLUE, lw=2.5, label=f"XGBoost (AUC={auc:.3f})")
ax.plot([0,1],[0,1], color=MUTED, lw=1, linestyle="--", label="Random")
ax.fill_between(fpr, tpr, alpha=0.08, color=BLUE)
ax.set_xlabel("FPR", color=MUTED, fontsize=9); ax.set_ylabel("TPR", color=MUTED, fontsize=9)
ax.legend(fontsize=8, facecolor="#1c2128", labelcolor=WHITE)
ax.text(0.55, 0.12, f"Gini = {gini:.3f}", color=GREEN, fontsize=12, fontweight="bold", transform=ax.transAxes)

prec, rec, _ = precision_recall_curve(y_test, y_proba)
ax = fig.add_subplot(r1[1]); style_ax(ax, f"② Precision-Recall  (AP={ap:.3f})")
ax.plot(rec, prec, color=YELLOW, lw=2.5)
ax.fill_between(rec, prec, alpha=0.08, color=YELLOW)
ax.axhline(y_test.mean(), color=RED, linestyle="--", lw=1, label=f"Baseline ({y_test.mean():.1%})")
ax.set_xlabel("Recall", color=MUTED, fontsize=9); ax.set_ylabel("Precision", color=MUTED, fontsize=9)
ax.legend(fontsize=8, facecolor="#1c2128", labelcolor=WHITE)

ax = fig.add_subplot(r1[2]); style_ax(ax, "③ Score Distribution by Label")
ax.hist(y_proba[y_test==0], bins=40, alpha=0.65, color=GREEN, label="Non-Default", density=True)
ax.hist(y_proba[y_test==1], bins=40, alpha=0.65, color=RED,   label="Default",     density=True)
ax.axvline(0.5, color=WHITE, linestyle="--", lw=1)
ax.set_xlabel("Predicted Probability", color=MUTED, fontsize=9)
ax.legend(fontsize=8, facecolor="#1c2128", labelcolor=WHITE)

r2 = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=outer[1], wspace=0.38)
ax = fig.add_subplot(r2[0]); style_ax(ax, f"④ KS Chart  (KS={ks:.3f})")
ax.plot(roc_thresh[::-1], tpr[::-1], color=GREEN, lw=2, label="TPR")
ax.plot(roc_thresh[::-1], fpr[::-1], color=RED,   lw=2, label="FPR")
ax.axvline(ks_thresh, color=YELLOW, linestyle="--", lw=1.5, label=f"KS threshold={ks_thresh:.2f}")
ax.set_xlabel("Score Threshold", color=MUTED, fontsize=9)
ax.legend(fontsize=8, facecolor="#1c2128", labelcolor=WHITE)

thresholds = np.arange(0.20, 0.85, 0.05)
precisions, recalls, f1s, approval_rates = [], [], [], []
for t in thresholds:
    p_ = (y_proba >= t).astype(int)
    cm = confusion_matrix(y_test, p_); tn,fp,fn,tp_ = cm.ravel()
    pr = tp_/(tp_+fp+1e-9); rc = tp_/(tp_+fn+1e-9)
    precisions.append(pr); recalls.append(rc)
    f1s.append(2*pr*rc/(pr+rc+1e-9)); approval_rates.append(1-p_.mean())

ax = fig.add_subplot(r2[1]); style_ax(ax, "⑤ Threshold Sensitivity")
ax.plot(thresholds, precisions,     color=GREEN,  lw=2, label="Precision")
ax.plot(thresholds, recalls,        color=RED,    lw=2, label="Recall")
ax.plot(thresholds, f1s,            color=BLUE,   lw=2, label="F1")
ax.plot(thresholds, approval_rates, color=YELLOW, lw=2, linestyle="--", label="Approval Rate")
ax.axvline(0.5, color=MUTED, linestyle=":", lw=1)
ax.set_xlabel("Threshold", color=MUTED, fontsize=9)
ax.legend(fontsize=8, facecolor="#1c2128", labelcolor=WHITE)

r3 = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=outer[2])
ax = fig.add_subplot(r3[0]); style_ax(ax, "⑥ Feature Importance (XGBoost Gain)")
top = fi_df.head(16)
cols = [RED if v > top["importance"].quantile(0.75) else
        YELLOW if v > top["importance"].quantile(0.40) else BLUE
        for v in top["importance"]]
bars = ax.barh(top["feature"][::-1], top["importance"][::-1], color=cols[::-1], edgecolor=BG, height=0.65)
for bar, val in zip(bars, top["importance"][::-1]):
    ax.text(bar.get_width()+0.001, bar.get_y()+bar.get_height()/2,
            f"{val:.4f}", va="center", fontsize=8, color=MUTED)
ax.set_xlabel("Importance (Gain)", color=MUTED, fontsize=9)
ax.set_xlim(0, top["importance"].max()*1.18)

r4 = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=outer[3])
ax = fig.add_subplot(r4[0]); ax.axis("off"); ax.set_facecolor(PANEL)
ax.text(0.01, 0.97, "⑦  Model Summary & Credit Benchmarks",
        fontsize=13, color=MUTED, fontweight="bold",
        transform=ax.transAxes, va="top", family="monospace")
rows = [
    ("AUC-ROC",      f"{auc:.4f}",       "> 0.75 Acceptable | > 0.85 Strong"),
    ("Gini",         f"{gini:.4f}",       "> 0.50 Acceptable | > 0.70 Strong"),
    ("KS Statistic", f"{ks:.4f}",         "> 0.25 Acceptable | > 0.40 Excellent"),
    ("Avg Precision",f"{ap:.4f}",         "Precision-Recall AUC"),
    ("KS Threshold", f"{ks_thresh:.3f}",  "Optimal decision cutoff"),
]
for j,(metric,val,bench) in enumerate(rows):
    y_ = 0.80 - j*0.15
    ax.text(0.01, y_, metric, fontsize=11, color=BLUE,  transform=ax.transAxes, va="top", fontweight="bold")
    ax.text(0.18, y_, val,    fontsize=13, color=WHITE, transform=ax.transAxes, va="top", fontweight="bold")
    ax.text(0.30, y_, bench,  fontsize=9,  color=MUTED, transform=ax.transAxes, va="top", style="italic")

out = os.path.join(REPORTS_DIR, "model_evaluation.png")
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
print(f"\n✅ Report saved → {out}")

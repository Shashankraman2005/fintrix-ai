"""
MSME Scorecard — Band Calibration
===================================
Finds optimal score band cutoffs from actual score distribution.
Prints the new cutoffs to paste into scorecard.py.
Run: python scripts/calibrate_bands.py
"""
import os
import pandas as pd
import numpy as np

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

df = pd.read_csv(os.path.join(REPORTS_DIR, "scorecard_results.csv"))

print(f"Score range : {df['credit_score'].min()} – {df['credit_score'].max()}")
print(f"Mean        : {df['credit_score'].mean():.1f}")
print(f"Std         : {df['credit_score'].std():.1f}")
print(f"\nPercentile distribution:")
for p in [5, 10, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90, 95]:
    print(f"  P{p:<3}: {np.percentile(df['credit_score'], p):.1f}")

# Calibrate cutoffs to match target portfolio split: 25/35/25/15
# GREEN  top 25%  → approve
# AMBER  next 25% → conditional
# YELLOW next 25% → review
# RED    bottom 25% → decline
p75 = np.percentile(df['credit_score'], 75)
p50 = np.percentile(df['credit_score'], 50)
p25 = np.percentile(df['credit_score'], 25)

print(f"\nCalibrated band cutoffs (percentile-based):")
print(f"  GREEN  : {int(p75)} – {df['credit_score'].max()}")
print(f"  AMBER  : {int(p50)} – {int(p75)-1}")
print(f"  YELLOW : {int(p25)} – {int(p50)-1}")
print(f"  RED    : {df['credit_score'].min()} – {int(p25)-1}")

# Validate — show default rate per band with new cutoffs
print(f"\nDefault rate validation with new cutoffs:")
conditions = [
    ("GREEN",  df['credit_score'] >= p75),
    ("AMBER",  (df['credit_score'] >= p50) & (df['credit_score'] < p75)),
    ("YELLOW", (df['credit_score'] >= p25) & (df['credit_score'] < p50)),
    ("RED",    df['credit_score'] < p25),
]
for band, mask in conditions:
    sub = df[mask]
    dr  = sub['actual_default'].mean()
    print(f"  {band:<8} n={mask.sum():<5} default_rate={dr:.1%}")

print(f"\nCopy these values into scorecard.py BANDS list:")
print(f"  ({int(p75)}, {df['credit_score'].max()}, 'GREEN',  'Approve',                '#2ecc71'),")
print(f"  ({int(p50)}, {int(p75)-1}, 'AMBER',  'Approve with Conditions', '#f39c12'),")
print(f"  ({int(p25)}, {int(p50)-1}, 'YELLOW', 'Manual Review',           '#f1c40f'),")
print(f"  ({df['credit_score'].min()}, {int(p25)-1}, 'RED',    'Decline',                '#e74c3c'),")

"""GST Portal filing history simulator."""
import json, os
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

rng = np.random.default_rng(42)
TODAY = datetime(2026, 3, 23)

PROFILES = {
    "full_data_good_kirana": {
        "filing_rate": 0.90, "monthly_avg_turnover": 180000,
        "business_vintage_months": 42,
    },
    "partial_data_growing_msme": {
        "filing_rate": 0.75, "monthly_avg_turnover": 340000,
        "business_vintage_months": 18,
    },
    "new_business_clean": {
        "filing_rate": 1.0, "monthly_avg_turnover": 72000,
        "business_vintage_months": 5,
    },
}


def generate(profile_name: str) -> dict:
    p = PROFILES[profile_name]
    bvm = p["business_vintage_months"]
    reg_date = TODAY - timedelta(days=bvm * 30)

    filings = []
    bank_credits = []
    cursor = datetime(reg_date.year, reg_date.month, 1)

    while cursor < TODAY:
        period = cursor.strftime("%Y-%m")
        next_month = cursor + relativedelta(months=1)
        due_dt = datetime(next_month.year, next_month.month, 20)

        is_filed = rng.random() < p["filing_rate"]
        if is_filed:
            days_delay = max(0, int(rng.normal(2, 3)))
            filed_dt = due_dt + timedelta(days=days_delay)
            status = "FILED" if days_delay == 0 else "FILED_LATE"
            filed_date = filed_dt.strftime("%Y-%m-%d")
        else:
            filed_date = None
            status = "NOT_FILED"

        turnover = round(float(p["monthly_avg_turnover"] * rng.normal(1, 0.15)), 2)
        turnover = max(1000, turnover)
        tax = round(turnover * 0.18, 2)

        filings.append({
            "period": period,
            "return_type": "GSTR-3B",
            "due_date": due_dt.strftime("%Y-%m-%d"),
            "filed_date": filed_date,
            "status": status,
            "declared_turnover": turnover,
            "tax_paid": tax,
        })

        bank_credit = round(float(turnover * rng.uniform(0.85, 1.20)), 2)
        bank_credits.append({
            "month": period,
            "total_credits": bank_credit,
        })

        cursor = next_month

    gstin = f"29AABCT{rng.integers(1000, 9999)}F1Z{rng.integers(1, 9)}"
    return {
        "gstin": gstin,
        "business_name": f"Demo MSME ({profile_name})",
        "registration_date": reg_date.strftime("%Y-%m-%d"),
        "data_as_of": TODAY.strftime("%Y-%m-%d"),
        "filings": filings,
        "bank_credits_monthly": bank_credits,
    }


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "demo_data", "middleman")
    os.makedirs(out_dir, exist_ok=True)
    total = 0
    for name in PROFILES:
        doc = generate(name)
        path = os.path.join(out_dir, f"{name}_gst.json")
        with open(path, "w") as f:
            json.dump(doc, f, indent=2)
        n = len(doc["filings"])
        total += n
        print(f"  ✓ {name}: {n} filings")
    print(f"gst_simulator       : {total} filings generated for {len(PROFILES)} profiles")

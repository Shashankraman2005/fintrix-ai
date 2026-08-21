"""Telecom operator SIM + recharge history simulator."""
import json, os
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

rng = np.random.default_rng(42)
TODAY = datetime(2026, 3, 23)

PROFILES = {
    "full_data_good_kirana": {
        "sim_age_days": 1500, "monthly_recharge": 399, "drop_rate": 0.0,
    },
    "partial_data_growing_msme": {
        "sim_age_days": 900, "monthly_recharge": 599, "drop_rate": 0.0,
    },
    "new_business_clean": {
        "sim_age_days": 2000, "monthly_recharge": 299, "drop_rate": 0.0,
    },
}


def generate(profile_name: str) -> dict:
    p = PROFILES[profile_name]
    sim_reg = TODAY - timedelta(days=p["sim_age_days"])

    recharge_history = []
    location_history = []
    cursor = datetime(sim_reg.year, sim_reg.month, 1)
    total_months = 0

    while cursor < TODAY:
        period = cursor.strftime("%Y-%m")
        base = p["monthly_recharge"]

        months_from_end = (TODAY.year - cursor.year) * 12 + (TODAY.month - cursor.month)
        if months_from_end < 3 and p["drop_rate"] > 0:
            amount = round(float(base * (1 - p["drop_rate"]) * rng.normal(1, 0.1)), 2)
        else:
            amount = round(float(base * rng.normal(1.0, 0.10)), 2)
        amount = max(49, amount)

        recharge_history.append({
            "month": period,
            "recharge_amount": amount,
            "recharge_count": int(rng.integers(1, 4)),
            "plan_type": "PREPAID",
        })

        location_history.append({
            "month": period,
            "primary_location": "Pune, Maharashtra",
            "location_changes": 0,
        })

        cursor += relativedelta(months=1)
        total_months += 1

    return {
        "operator": "Jio",
        "sim_registration_date": sim_reg.strftime("%Y-%m-%d"),
        "number": f"+919{rng.integers(100000000, 999999999)}",
        "data_as_of": TODAY.strftime("%Y-%m-%d"),
        "location_history": location_history,
        "recharge_history": recharge_history,
        "device_history": [],
    }


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "demo_data", "middleman")
    os.makedirs(out_dir, exist_ok=True)
    total = 0
    for name in PROFILES:
        doc = generate(name)
        n = len(doc["recharge_history"])
        total += n
        path = os.path.join(out_dir, f"{name}_telecom.json")
        with open(path, "w") as f:
            json.dump(doc, f, indent=2)
        print(f"  ✓ {name}: {n} months")
    print(f"telecom_simulator   : {total} months generated for {len(PROFILES)} profiles")

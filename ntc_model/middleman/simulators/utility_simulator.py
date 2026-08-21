"""Utility company bill payment history simulator."""
import json, os, uuid
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

rng = np.random.default_rng(42)
TODAY = datetime(2026, 3, 23)

PROFILES = {
    "full_data_good_kirana": {
        "on_time_rate": 0.88, "base_amount": 2200, "avg_dpd": 3,
        "base_units": 220, "connection_type": "COMMERCIAL",
        "business_vintage_months": 42,
    },
    "minimal_data_stressed": {
        "on_time_rate": 0.40, "base_amount": 1800, "avg_dpd": 18,
        "base_units": 180, "connection_type": "COMMERCIAL",
        "business_vintage_months": 10,
    },
}


def generate(profile_name: str) -> dict:
    p = PROFILES[profile_name]
    bvm = p["business_vintage_months"]
    conn_date = TODAY - timedelta(days=bvm * 30)

    bills = []
    cursor = datetime(conn_date.year, conn_date.month, 1)

    while cursor < TODAY:
        bill_dt = datetime(cursor.year, cursor.month, 5)
        due_dt = datetime(cursor.year, cursor.month, 20)
        amount = round(float(p["base_amount"] * rng.normal(1.0, 0.15)), 2)
        amount = max(200, amount)
        units = round(float(p["base_units"] * rng.normal(1.0, 0.12)), 1)
        units = max(10, units)

        is_on_time = rng.random() < p["on_time_rate"]

        if is_on_time:
            pd_dt = due_dt - timedelta(days=int(rng.integers(0, 6)))
            paid_date = pd_dt.strftime("%Y-%m-%d")
            status = "PAID"
        elif (TODAY - due_dt).days < 25:
            paid_date = None
            status = "UNPAID"
        else:
            dpd = max(1, int(rng.normal(p["avg_dpd"], p["avg_dpd"] * 0.3)))
            pd_dt = due_dt + timedelta(days=dpd)
            paid_date = pd_dt.strftime("%Y-%m-%d")
            status = "PAID_LATE"

        bills.append({
            "bill_id": f"BILL-{uuid.uuid4().hex[:8].upper()}",
            "bill_date": bill_dt.strftime("%Y-%m-%d"),
            "due_date": due_dt.strftime("%Y-%m-%d"),
            "paid_date": paid_date,
            "amount": amount,
            "units_consumed": units,
            "status": status,
        })

        cursor += relativedelta(months=1)

    return {
        "provider": "BESCOM Electricity",
        "consumer_number": f"BESCOM-{rng.integers(100000, 999999)}",
        "connection_date": conn_date.strftime("%Y-%m-%d"),
        "connection_type": p["connection_type"],
        "data_as_of": TODAY.strftime("%Y-%m-%d"),
        "bills": bills,
    }


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "demo_data", "middleman")
    os.makedirs(out_dir, exist_ok=True)
    total = 0
    for name in PROFILES:
        doc = generate(name)
        n = len(doc["bills"])
        total += n
        path = os.path.join(out_dir, f"{name}_utility.json")
        with open(path, "w") as f:
            json.dump(doc, f, indent=2)
        print(f"  ✓ {name}: {n} bills")
    print(f"utility_simulator   : {total} bills generated for {len(PROFILES)} profiles")

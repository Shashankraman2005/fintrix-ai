"""Supplier/Wholesaler invoice history simulator."""
import json, os, uuid
import numpy as np
from datetime import datetime, timedelta

rng = np.random.default_rng(42)
TODAY = datetime(2026, 3, 23)

PROFILES = {
    "full_data_good_kirana": {
        "avg_invoice": 45000, "on_time_rate": 0.92, "avg_dpd": 2,
        "business_vintage_months": 42,
    },
    "partial_data_growing_msme": {
        "avg_invoice": 85000, "on_time_rate": 0.72, "avg_dpd": 8,
        "business_vintage_months": 18,
    },
    # minimal_data_stressed: NO supplier data
    "new_business_clean": {
        "avg_invoice": 18000, "on_time_rate": 0.88, "avg_dpd": 3,
        "business_vintage_months": 5,
    },
}


def generate(profile_name: str) -> dict:
    p = PROFILES[profile_name]
    bvm = p["business_vintage_months"]
    start = TODAY - timedelta(days=bvm * 30)
    reg_date = start.strftime("%Y-%m-%d")

    invoices = []
    cursor = start
    while cursor < TODAY:
        gap = int(rng.integers(5, 9))
        cursor += timedelta(days=gap)
        if cursor >= TODAY:
            break

        amount = round(float(p["avg_invoice"] * rng.normal(1.0, 0.20)), 2)
        amount = max(500, amount)
        inv_date = cursor.strftime("%Y-%m-%d")
        due_days = int(rng.integers(15, 31))
        due_dt = cursor + timedelta(days=due_days)
        due_date = due_dt.strftime("%Y-%m-%d")

        is_on_time = rng.random() < p["on_time_rate"]

        if is_on_time:
            pd_dt = due_dt - timedelta(days=int(rng.integers(0, 4)))
            paid_date = pd_dt.strftime("%Y-%m-%d")
            status = "PAID"
            pmode = rng.choice(["CASH", "UPI", "NEFT"])
        elif (TODAY - due_dt).days < 20:
            paid_date = None
            status = "OUTSTANDING"
            pmode = None
        else:
            dpd = max(1, int(rng.normal(p["avg_dpd"], p["avg_dpd"] * 0.3)))
            pd_dt = due_dt + timedelta(days=dpd)
            paid_date = pd_dt.strftime("%Y-%m-%d")
            pmode = rng.choice(["CASH", "UPI", "NEFT"])
            if dpd > 60:
                status = "DEFAULTED"
            elif dpd > 30:
                status = "OVERDUE"
            else:
                status = "PAID_LATE"

        invoices.append({
            "invoice_id": f"INV-{uuid.uuid4().hex[:8].upper()}",
            "invoice_date": inv_date,
            "due_date": due_date,
            "paid_date": paid_date,
            "amount": amount,
            "status": status,
            "payment_mode": str(pmode) if pmode is not None else None,
        })

    otr = p["on_time_rate"]
    if otr > 0.85:
        disputes = 0
        rating = "EXCELLENT"
    elif otr > 0.70:
        disputes = int(rng.integers(0, 2))
        rating = "GOOD"
    elif otr > 0.50:
        disputes = int(rng.integers(1, 3))
        rating = "FAIR"
    else:
        disputes = int(rng.integers(2, 5))
        rating = "POOR"

    return {
        "supplier_name": f"M/s Wholesale Traders ({profile_name})",
        "msme_id": f"MSME_{profile_name.upper()}",
        "registration_date": reg_date,
        "data_as_of": TODAY.strftime("%Y-%m-%d"),
        "invoices": invoices,
        "supplier_reference": {
            "years_known": round(bvm / 12, 1),
            "credit_limit_extended": round(p["avg_invoice"] * 1.8, 2),
            "disputes_raised": disputes,
            "reference_rating": rating,
        },
    }


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "demo_data", "middleman")
    os.makedirs(out_dir, exist_ok=True)
    total_inv = 0
    for name in PROFILES:
        doc = generate(name)
        path = os.path.join(out_dir, f"{name}_supplier.json")
        with open(path, "w") as f:
            json.dump(doc, f, indent=2)
        n = len(doc["invoices"])
        total_inv += n
        print(f"  ✓ {name}: {n} invoices")
    print(f"supplier_simulator  : {total_inv} invoices generated for {len(PROFILES)} profiles")

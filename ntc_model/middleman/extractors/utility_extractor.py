"""Extract credit features from utility company bill data."""
from datetime import datetime
from collections import defaultdict


def extract(utility_data: dict) -> dict:
    bills = utility_data.get("bills", [])
    if not bills:
        return {"data_source_utility": True}

    conn_date = datetime.strptime(utility_data["connection_date"], "%Y-%m-%d")
    as_of = datetime.strptime(utility_data["data_as_of"], "%Y-%m-%d")
    months = max(1, (as_of - conn_date).days / 30)

    paid = [b for b in bills if b["status"] in ("PAID", "PAID_LATE")]
    on_time = [b for b in bills if b["status"] == "PAID"]
    late = [b for b in bills if b["status"] == "PAID_LATE"]
    unpaid = [b for b in bills if b["status"] == "UNPAID"]

    # utility_payment_consistency
    denom = max(1, len(paid) + len(unpaid))
    upc = round(len(on_time) / denom, 4)

    # avg_utility_dpd
    dpd_vals = []
    for b in late:
        if b.get("paid_date") and b.get("due_date"):
            pd = datetime.strptime(b["paid_date"], "%Y-%m-%d")
            dd = datetime.strptime(b["due_date"], "%Y-%m-%d")
            dpd_vals.append(max(0, (pd - dd).days))
    avg_dpd = round(sum(dpd_vals) / len(dpd_vals), 2) if dpd_vals else 0.0
    avg_dpd = min(90, avg_dpd)

    # min_balance_violation_count
    late_months = set()
    for b in late + unpaid:
        dt = datetime.strptime(b["bill_date"], "%Y-%m-%d")
        late_months.add(f"{dt.year}-{dt.month:02d}")
    mbvc = min(8, len(late_months))

    # eod_balance_volatility (proxy from utility consistency)
    ebv = round(min(1.0, max(0, (1 - upc) * 0.7 + 0.1)), 4)

    # business_vintage_months
    bvm = round((as_of - conn_date).days / 30, 1)

    return {
        "utility_payment_consistency": upc,
        "avg_utility_dpd": avg_dpd,
        "min_balance_violation_count": mbvc,
        "eod_balance_volatility": ebv,
        "business_vintage_months": bvm,
        "data_source_utility": True,
    }

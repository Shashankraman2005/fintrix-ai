"""Extract credit features from supplier/wholesaler invoice data."""
import math
from datetime import datetime
from collections import defaultdict


def extract(supplier_data: dict) -> dict:
    invoices = supplier_data.get("invoices", [])
    if not invoices:
        return {"data_source_supplier": True}

    reg_date = datetime.strptime(supplier_data["registration_date"], "%Y-%m-%d")
    as_of = datetime.strptime(supplier_data["data_as_of"], "%Y-%m-%d")
    months = max(1, (as_of - reg_date).days / 30)

    paid = [i for i in invoices if i["status"] in ("PAID", "PAID_LATE")]
    on_time = [i for i in invoices if i["status"] == "PAID"]
    late = [i for i in invoices if i["status"] == "PAID_LATE"]
    defaulted = [i for i in invoices if i["status"] == "DEFAULTED"]
    outstanding = [i for i in invoices if i["status"] in ("OUTSTANDING", "OVERDUE")]

    # vendor_payment_discipline
    denom = max(1, len(paid) + len(defaulted))
    vendor_payment_discipline = round(len(on_time) / denom, 4)

    # avg_invoice_payment_delay
    dpd_vals = []
    for inv in late + defaulted:
        if inv.get("paid_date") and inv.get("due_date"):
            pd = datetime.strptime(inv["paid_date"], "%Y-%m-%d")
            dd = datetime.strptime(inv["due_date"], "%Y-%m-%d")
            dpd_vals.append(max(0, (pd - dd).days))
    avg_delay = round(sum(dpd_vals) / len(dpd_vals), 2) if dpd_vals else 0.0
    avg_delay = min(90, avg_delay)

    # business_vintage_months
    bvm = round((as_of - reg_date).days / 30, 1)

    # cashflow_volatility
    monthly_totals = defaultdict(float)
    for inv in paid:
        dt = datetime.strptime(inv["invoice_date"], "%Y-%m-%d")
        monthly_totals[f"{dt.year}-{dt.month:02d}"] += inv["amount"]
    vals = list(monthly_totals.values())
    if len(vals) < 3:
        cv = 0.4
    else:
        m = sum(vals) / len(vals)
        std = (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5
        cv = round(min(1.0, max(0.0, std / (m + 1))), 4)

    # revenue_growth_trend
    sorted_months = sorted(monthly_totals.keys())
    if len(sorted_months) < 4:
        trend = 0.0
    else:
        mid = len(sorted_months) // 2
        first_half = [monthly_totals[k] for k in sorted_months[:mid]]
        second_half = [monthly_totals[k] for k in sorted_months[mid:]]
        f_avg = sum(first_half) / len(first_half)
        s_avg = sum(second_half) / len(second_half)
        trend = round(max(-1.0, min(1.0, (s_avg - f_avg) / (f_avg + 1))), 4)

    # operating_cashflow_ratio
    total_paid = sum(i["amount"] for i in paid)
    total_all = sum(i["amount"] for i in invoices)
    ocr = round(total_paid / (total_all + 1), 4) if total_all > 0 else 0.75

    # bounced_transaction_count
    bounce = len(defaulted) * 2 + len([i for i in outstanding if i["status"] == "OVERDUE"])
    bounce = min(10, bounce)

    # turnover_inflation_spike
    if sorted_months:
        last_month_key = sorted_months[-1]
        last_total = monthly_totals[last_month_key]
        prev_vals = [monthly_totals[k] for k in sorted_months[:-1]]
        prev_avg = sum(prev_vals) / len(prev_vals) if prev_vals else 1
        tis = 1 if last_total > prev_avg * 3 else 0
    else:
        tis = 0

    # benford_anomaly_score
    amounts = [i["amount"] for i in invoices if i["amount"] > 0]
    if len(amounts) < 10:
        benford = 0.15
    else:
        first_digits = [int(str(int(abs(a)))[0]) for a in amounts if int(abs(a)) > 0]
        expected = [math.log10(1 + 1 / d) for d in range(1, 10)]
        counts = [0] * 9
        for d in first_digits:
            if 1 <= d <= 9:
                counts[d - 1] += 1
        total_d = sum(counts) or 1
        observed = [c / total_d for c in counts]
        benford = round(min(1.0, sum(abs(o - e) for o, e in zip(observed, expected)) / 2.0), 4)

    # round_number_spike_ratio
    round_count = sum(1 for i in invoices if i["amount"] % 1000 == 0 or i["amount"] % 500 == 0)
    rnsr = round(round_count / max(1, len(invoices)), 4)

    # customer_concentration from reference
    ref = supplier_data.get("supplier_reference", {})
    rating = ref.get("reference_rating", "FAIR")
    ccr_map = {"EXCELLENT": 0.25, "GOOD": 0.45, "FAIR": 0.65, "POOR": 0.82}
    ccr = ccr_map.get(rating, 0.55)

    # repeat_customer_revenue_pct
    years_known = ref.get("years_known", 1.0)
    rcrp = min(1.0, years_known / 2.0)

    return {
        "vendor_payment_discipline": vendor_payment_discipline,
        "avg_invoice_payment_delay": avg_delay,
        "business_vintage_months": bvm,
        "cashflow_volatility": cv,
        "revenue_growth_trend": trend,
        "operating_cashflow_ratio": ocr,
        "bounced_transaction_count": bounce,
        "turnover_inflation_spike": tis,
        "benford_anomaly_score": benford,
        "round_number_spike_ratio": rnsr,
        "customer_concentration_ratio": ccr,
        "repeat_customer_revenue_pct": rcrp,
        "data_source_supplier": True,
    }

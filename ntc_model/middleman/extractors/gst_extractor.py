"""Extract credit features from GST portal filing data."""
from datetime import datetime
from collections import defaultdict


def extract(gst_data: dict) -> dict:
    filings = gst_data.get("filings", [])
    bank_credits = gst_data.get("bank_credits_monthly", [])
    if not filings:
        return {"data_source_gst": True}

    reg_date = datetime.strptime(gst_data["registration_date"], "%Y-%m-%d")
    as_of = datetime.strptime(gst_data["data_as_of"], "%Y-%m-%d")
    total = max(1, len(filings))

    filed = [f for f in filings if f["status"] in ("FILED", "FILED_LATE")]
    not_filed = [f for f in filings if f["status"] == "NOT_FILED"]

    # gst_filing_consistency_score
    gfcs = round((len(filed) / total) * 10, 2)
    gfcs = min(10, max(0, gfcs))

    # gst_to_bank_variance
    bank_map = {b["month"]: b["total_credits"] for b in bank_credits}
    variances = []
    for f in filed:
        period = f["period"]
        if period in bank_map and bank_map[period] > 0:
            declared = f["declared_turnover"]
            bank = bank_map[period]
            v = abs(declared - bank) / (bank + 1)
            variances.append(v)
    gtbv = round(sum(variances) / len(variances), 4) if variances else 0.30
    gtbv = min(3.0, max(0, gtbv))

    # revenue_seasonality_index
    monthly_by_cal = defaultdict(float)
    for f in filed:
        dt = datetime.strptime(f["period"] + "-01", "%Y-%m-%d")
        monthly_by_cal[dt.month] += f["declared_turnover"]
    if len(filed) < 6:
        rsi = 0.2
    else:
        cal_vals = list(monthly_by_cal.values())
        avg_m = sum(cal_vals) / len(cal_vals) if cal_vals else 1
        max_m = max(cal_vals) if cal_vals else 0
        rsi = round(min(1.0, max(0, (max_m - avg_m) / (avg_m + 1))), 4)

    # business_vintage_months
    bvm = round((as_of - reg_date).days / 30, 1)

    # revenue_growth_trend
    sorted_filings = sorted(filed, key=lambda x: x["period"])
    if len(sorted_filings) < 4:
        trend = 0.0
    else:
        mid = len(sorted_filings) // 2
        first_half = [f["declared_turnover"] for f in sorted_filings[:mid]]
        second_half = [f["declared_turnover"] for f in sorted_filings[mid:]]
        f_avg = sum(first_half) / len(first_half)
        s_avg = sum(second_half) / len(second_half)
        trend = round(max(-1.0, min(1.0, (s_avg - f_avg) / (f_avg + 1))), 4)

    return {
        "gst_filing_consistency_score": gfcs,
        "gst_to_bank_variance": gtbv,
        "revenue_seasonality_index": rsi,
        "business_vintage_months": bvm,
        "revenue_growth_trend": trend,
        "data_source_gst": True,
    }

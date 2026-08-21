"""Extract credit features from telecom operator data."""
from datetime import datetime


def extract(telecom_data: dict) -> dict:
    as_of = datetime.strptime(telecom_data["data_as_of"], "%Y-%m-%d")
    sim_reg = datetime.strptime(telecom_data["sim_registration_date"], "%Y-%m-%d")

    # telecom_number_vintage_days
    vintage = max(0, min(3650, (as_of - sim_reg).days))

    # telecom_recharge_drop_ratio
    recharges = telecom_data.get("recharge_history", [])
    amounts = [r["recharge_amount"] for r in recharges]
    if len(amounts) < 3:
        drop = 0.15
    else:
        recent_3 = sum(amounts[-3:]) / 3
        earlier = amounts[:-3]
        if earlier:
            earlier_avg = sum(earlier) / len(earlier)
            if earlier_avg == 0:
                drop = 0.15
            else:
                drop = round(max(0, min(1, (earlier_avg - recent_3) / earlier_avg)), 4)
        else:
            drop = 0.15

    # identity_device_mismatch
    device_events = telecom_data.get("device_history", [])
    recent_cutoff = datetime(as_of.year, as_of.month, as_of.day)
    from datetime import timedelta
    cutoff = recent_cutoff - timedelta(days=180)
    recent_events = [e for e in device_events
                     if datetime.strptime(e["date"], "%Y-%m-%d") >= cutoff]
    swaps = sum(1 for e in recent_events if e["event"] == "SIM_SWAP")
    changes = sum(1 for e in recent_events if e["event"] == "DEVICE_CHANGE")
    idm = 1 if (swaps + changes) >= 2 else 0

    # cash_withdrawal_dependency proxy from plan type
    if recharges:
        latest = recharges[-1]
        cwd = 0.65 if latest.get("plan_type") == "PREPAID" else 0.25
    else:
        cwd = 0.40

    return {
        "telecom_number_vintage_days": vintage,
        "telecom_recharge_drop_ratio": drop,
        "identity_device_mismatch": idm,
        "cash_withdrawal_dependency": cwd,
        "data_source_telecom": True,
    }

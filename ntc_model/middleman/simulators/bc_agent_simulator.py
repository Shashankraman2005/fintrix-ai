"""BC Agent / Kirana cash deposit + field verification simulator."""
import json, os, uuid
import numpy as np
from datetime import datetime, timedelta

rng = np.random.default_rng(42)
TODAY = datetime(2026, 3, 23)

PROFILES = {
    "full_data_good_kirana": {
        "weekly_avg": 8000, "agent_network": "FINO",
        "business_vintage_months": 42, "irregular": False,
        "field_verified": True,
    },
    "minimal_data_stressed": {
        "weekly_avg": 3000, "agent_network": "EKO",
        "business_vintage_months": 10, "irregular": True,
        "field_verified": False,
    },
}


def generate(profile_name: str) -> dict:
    p = PROFILES[profile_name]
    bvm = p["business_vintage_months"]
    first_txn = TODAY - timedelta(days=bvm * 30)

    transactions = []
    cursor = first_txn
    balance = 0.0

    while cursor < TODAY:
        if p["irregular"]:
            gap = int(rng.integers(5, 14))
            skip = rng.random() < 0.25
        else:
            gap = int(rng.integers(6, 9))
            skip = False

        cursor += timedelta(days=gap)
        if cursor >= TODAY:
            break
        if skip:
            continue

        dep_amt = round(float(p["weekly_avg"] * rng.normal(1.0, 0.25)), 2)
        dep_amt = max(200, dep_amt)
        balance += dep_amt
        transactions.append({
            "date": cursor.strftime("%Y-%m-%d"),
            "type": "CASH_DEPOSIT",
            "amount": dep_amt,
            "balance_after": round(balance, 2),
        })

        if p["irregular"] and rng.random() < 0.4:
            wd = round(float(dep_amt * rng.uniform(0.6, 1.3)), 2)
            balance -= wd
            transactions.append({
                "date": cursor.strftime("%Y-%m-%d"),
                "type": "CASH_WITHDRAWAL",
                "amount": wd,
                "balance_after": round(balance, 2),
            })
        elif not p["irregular"] and rng.random() < 0.15:
            wd = round(float(dep_amt * rng.uniform(0.2, 0.4)), 2)
            balance -= wd
            transactions.append({
                "date": cursor.strftime("%Y-%m-%d"),
                "type": "CASH_WITHDRAWAL",
                "amount": wd,
                "balance_after": round(balance, 2),
            })

    if p["field_verified"]:
        fv = {
            "verified": True,
            "verification_date": (TODAY - timedelta(days=30)).strftime("%Y-%m-%d"),
            "shop_exists": True,
            "stock_observed": True,
            "customers_present": True,
            "verifier_notes": "Shop operational, good stock levels, regular customers observed.",
        }
    else:
        fv = {
            "verified": False,
            "verification_date": None,
            "shop_exists": True,
            "stock_observed": False,
            "customers_present": False,
            "verifier_notes": "Shop exists but low activity. Could not verify stock.",
        }

    return {
        "agent_id": f"AGT-{rng.integers(1000, 9999)}",
        "agent_name": f"Agent ({p['agent_network']})",
        "agent_network": p["agent_network"],
        "msme_id": f"MSME_{profile_name.upper()}",
        "first_transaction_date": first_txn.strftime("%Y-%m-%d"),
        "data_as_of": TODAY.strftime("%Y-%m-%d"),
        "transactions": transactions,
        "field_verification": fv,
    }


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "demo_data", "middleman")
    os.makedirs(out_dir, exist_ok=True)
    total = 0
    for name in PROFILES:
        doc = generate(name)
        n = len(doc["transactions"])
        total += n
        path = os.path.join(out_dir, f"{name}_bc_agent.json")
        with open(path, "w") as f:
            json.dump(doc, f, indent=2)
        print(f"  ✓ {name}: {n} transactions")
    print(f"bc_agent_simulator  : {total} transactions for {len(PROFILES)} profiles")

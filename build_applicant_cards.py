"""
build_applicant_cards.py — Seed applicant_cards.db from demo_users.json

Runs each demo user through the full PDR scoring pipeline and saves the
result into SQLite so the chatbot can answer queries immediately.

Usage:
    python build_applicant_cards.py
    python build_applicant_cards.py --db path/to/other.db
"""

import argparse
import json
import pathlib
import sys

from context_layer import init_database, save_applicant_card
from scorer import score_user


DEMO_USERS_PATH = pathlib.Path(__file__).parent / "demo_users.json"
DEFAULT_DB = pathlib.Path(__file__).parent / "applicant_cards.db"

# NTC_004 has dynamic_income=true and empty transactions.
# We inject a minimal 12-month salary pattern so it can be scored.
_DEFAULT_MONTHLY_INCOME = 30_000  # ₹30K/month fallback

def _synthetic_transactions(monthly_income: float) -> list:
    """Generate 12 months of salary + fixed expenses for dynamic-income profiles."""
    txns = []
    for month in range(1, 13):
        txns.append({
            "date": f"2025-{month:02d}-01",
            "amount": monthly_income,
            "type": "credit",
            "narration": "SALARY CREDIT",
        })
        txns.append({
            "date": f"2025-{month:02d}-05",
            "amount": 8000,
            "type": "debit",
            "narration": "RENT PAYMENT",
        })
        txns.append({
            "date": f"2025-{month:02d}-10",
            "amount": 1500,
            "type": "debit",
            "narration": "UTILITY BILL",
        })
    return txns


def _applicant_id(user_id: str) -> str:
    """Normalise 'NTC_001' → 'ntc_001' to match chatbot router extraction."""
    return user_id.lower()


def build_cards(db_path: pathlib.Path) -> None:
    print(f"[INFO] Initialising database: {db_path}")
    init_database(str(db_path))

    raw = json.loads(DEMO_USERS_PATH.read_text(encoding="utf-8"))
    users = raw["demo_users"]
    print(f"[INFO] Found {len(users)} demo users\n")

    ok = 0
    failed = 0

    for user in users:
        uid = user["user_id"]
        applicant_id = _applicant_id(uid)
        profile = user.get("user_profile", {})
        gst_data = user.get("gst_data", {})
        transactions = user.get("transactions", [])

        # NTC_004 and any profile with dynamic_income / empty transactions
        if not transactions:
            annual_income = profile.get("annual_income", _DEFAULT_MONTHLY_INCOME * 12)
            monthly_income = annual_income / 12
            transactions = _synthetic_transactions(monthly_income)
            print(f"  [{uid}] No transactions - using synthetic income Rs{monthly_income:,.0f}/mo")

        try:
            result = score_user(transactions, profile, gst_data)

            name = profile.get("name", uid)
            city = profile.get("city", "")
            business_type = profile.get("business_type", "")

            save_applicant_card(
                db_path=str(db_path),
                scoring_result=result,
                applicant_id=applicant_id,
                name=name,
                city=city,
                business_type=business_type,
            )

            grade = result.get("grade", "?")
            outcome = result.get("outcome", "?")
            pd_val = result.get("default_probability")
            pd_str = f"{pd_val:.1%}" if pd_val is not None else "pre-layer"
            print(f"  [OK]  {uid:10s}  {grade} | {outcome} | PD={pd_str}  ({name})")
            ok += 1

        except Exception as exc:
            print(f"  [ERR] {uid}: {exc}", file=sys.stderr)
            failed += 1

    print(f"\n[DONE] {ok} saved, {failed} failed  |  DB: {db_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed applicant_cards.db from demo_users.json")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to SQLite database")
    args = parser.parse_args()

    build_cards(pathlib.Path(args.db))

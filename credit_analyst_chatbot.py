import pathlib
import sys
import traceback

from chatbot_router import route_query
from chatbot_context import build_prompt, fetch_applicant_context
from llm_client import call_ollama, OLLAMA_URL, MODEL
from response_formatter import format_response

# Always resolve DB relative to this file so it works from any working directory
DB = str(pathlib.Path(__file__).parent / "applicant_cards.db")


def _check_ollama() -> bool:
    """Return True if Ollama is reachable, else print an error and return False."""
    import requests  # already installed (used by llm_client)
    try:
        resp = requests.get(OLLAMA_URL.replace("/api/generate", ""), timeout=5)
        return resp.status_code < 500
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot reach Ollama at {OLLAMA_URL}")
        print("        Make sure Ollama is running:  ollama serve")
        print(f"        And the model is pulled:     ollama pull {MODEL}")
        return False
    except Exception:
        return True  # non-connection error — let it fail naturally on first query


def _check_db() -> bool:
    """Return True if the DB exists and has at least one applicant card."""
    db_path = pathlib.Path(DB)
    if not db_path.exists():
        print(f"[ERROR] Database not found: {DB}")
        print("        Run:  python build_applicant_cards.py")
        return False
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM applicant_cards").fetchone()[0]
        conn.close()
        if count == 0:
            print(f"[WARN]  Database exists but is empty.")
            print("        Run:  python build_applicant_cards.py")
        else:
            print(f"[INFO]  {count} applicant card(s) loaded from {db_path.name}")
        return True
    except Exception as exc:
        print(f"[WARN]  Could not verify DB contents: {exc}")
        return True


def main():
    print("=" * 50)
    print("  FintrixAi Credit Analyst Chatbot")
    print("=" * 50)

    if not _check_ollama():
        sys.exit(1)

    _check_db()

    print(f"  Model : {MODEL}")
    print(f"  DB    : {pathlib.Path(DB).name}")
    print("  Type 'exit' to quit\n")

    while True:
        try:
            query = input("Loan Officer > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not query:
            continue

        if query.lower() in ("exit", "quit"):
            print("Bye.")
            break

        try:
            routed = route_query(query)
            system_prompt, user_prompt = build_prompt(routed, DB)
            response = call_ollama(system_prompt, user_prompt, query_type=routed.query_type.value)

            # Fetch context for the formatter (needs applicant data for headers/sections)
            ctx = None
            ctx_b = None
            if routed.applicant_ids:
                ctx = fetch_applicant_context(DB, routed.applicant_ids[0])
            if len(routed.applicant_ids) > 1:
                ctx_b = fetch_applicant_context(DB, routed.applicant_ids[1])

            formatted = format_response(routed.query_type, response, ctx, ctx_b)
            print(formatted)
        except Exception as exc:
            print(f"[ERROR] {exc}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
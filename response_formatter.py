"""
response_formatter.py — FintrixAi Chatbot Response Formatter
=======================================================
Wraps raw LLM text in structured, loan-officer-friendly display blocks.

Each query type gets its own layout:
  LOOKUP          -> compact profile card
  EXPLANATION     -> full decision breakdown with risk factors
  COMPARISON      -> side-by-side table + analyst recommendation
  SCENARIO        -> what-if analysis block
  DECISION_LETTER -> clean letter layout
  RISK_ASSESSMENT -> primary risk + full factor list
  AGGREGATE       -> portfolio summary
"""

from chatbot_router import QueryType
from typing import Optional

_W = 57
_THICK = "=" * _W
_THIN  = "-" * _W


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _decision_label(decision: str) -> str:
    d = (decision or "UNKNOWN").upper()
    if "REJECTED" in d or "DECLINED" in d:
        return "APPLICATION REJECTED"
    if "APPROVED WITH CONDITIONS" in d or "CONDITIONAL" in d:
        return "APPROVED WITH CONDITIONS"
    if "APPROVED" in d:
        return "APPLICATION APPROVED"
    if "MANUAL" in d or "REVIEW" in d:
        return "REFERRED FOR MANUAL REVIEW"
    return d


def _decision_icon(decision: str) -> str:
    d = (decision or "").upper()
    if "REJECTED" in d or "DECLINED" in d:
        return "[X]"
    if "APPROVED WITH" in d or "CONDITION" in d:
        return "[~]"
    if "APPROVED" in d:
        return "[OK]"
    if "MANUAL" in d or "REVIEW" in d:
        return "[?]"
    return "[ ]"


def _header(title: str) -> str:
    return f"\n{_THICK}\n  {title}\n{_THICK}"


def _section(title: str) -> str:
    return f"\n{_THIN}\n  {title}\n{_THIN}"


def _applicant_block(ctx: dict) -> str:
    name   = ctx.get("name", "Unknown")
    aid    = ctx.get("applicant_id", "?").upper()
    city   = ctx.get("city", "?")
    btype  = ctx.get("business_type", "?")
    grade  = ctx.get("grade", "?")
    risk   = ctx.get("risk_band", "?")
    dec    = ctx.get("decision", "UNKNOWN")
    pd_val = ctx.get("default_probability", 0.0)
    pd_str = f"{pd_val:.1%}"

    return (
        f"\n"
        f"  APPLICANT  : {name} ({aid})\n"
        f"  TYPE/CITY  : {btype} | {city}\n"
        f"  GRADE      : {grade}   RISK BAND: {risk}   DEFAULT RISK: {pd_str}\n"
        f"  DECISION   : {dec}\n"
    )


def _shap_block(ctx: dict, max_factors: int = 5) -> str:
    factors = ctx.get("enriched_shap", [])[:max_factors]
    if not factors:
        return "  (No factor data available)\n"

    lines = []
    for f in factors:
        rank      = f.get("rank", "?")
        label     = f.get("label", f.get("feature", "unknown"))
        raw_val   = f.get("raw_value")
        direction = (f.get("direction") or "").lower()
        impact    = f.get("impact", "")

        # Format value
        if raw_val is None:
            val_str = ""
        elif isinstance(raw_val, float) and label.endswith(("score", "rate", "ratio", "dependency")):
            val_str = f" = {raw_val:.0%}"
        elif isinstance(raw_val, float):
            val_str = f" = {raw_val:.2f}"
        else:
            val_str = f" = {raw_val}"

        marker = "[RISK]" if direction == "risk" else "[OK]  "
        lines.append(f"  {rank}. {marker} {label}{val_str}")

    return "\n".join(lines) + "\n"


def _loan_offer_block(ctx: dict) -> str:
    offer_text = ctx.get("loan_offer_text", "")
    if offer_text:
        return f"  {offer_text}\n"
    return "  No standard loan offer. Consider alternative products.\n"


def _red_flags_block(ctx: dict) -> str:
    flags = ctx.get("red_flags", [])
    if not flags:
        return ""
    lines = [_section("  RED FLAGS DETECTED")]
    lines.append("")
    for f in flags:
        lines.append(f"  ! {f}")
    lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def format_response(
    query_type,
    llm_output: str,
    ctx: Optional[dict] = None,
    ctx_b: Optional[dict] = None,
) -> str:
    """
    Wrap LLM output in structured, human-readable display for the loan officer.

    Args:
        query_type : QueryType enum value (or string value)
        llm_output : Raw string returned by the LLM
        ctx        : Primary applicant context dict (from fetch_applicant_context)
        ctx_b      : Secondary applicant context (COMPARISON only)

    Returns:
        Formatted multi-line string ready to print.
    """
    qt = query_type

    if qt == QueryType.LOOKUP:
        return _fmt_lookup(llm_output, ctx)
    if qt == QueryType.EXPLANATION:
        return _fmt_explanation(llm_output, ctx)
    if qt == QueryType.COMPARISON:
        return _fmt_comparison(llm_output, ctx, ctx_b)
    if qt == QueryType.DECISION_LETTER:
        return _fmt_letter(llm_output, ctx)
    if qt == QueryType.SCENARIO:
        return _fmt_scenario(llm_output, ctx)
    if qt == QueryType.RISK_ASSESSMENT:
        return _fmt_risk_assessment(llm_output, ctx)
    if qt == QueryType.AGGREGATE:
        return _fmt_aggregate(llm_output)
    # UNKNOWN or fallback
    return f"\n{llm_output.strip()}\n"


# ─────────────────────────────────────────────────────────────────────────────
# PER-TYPE FORMATTERS
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_lookup(llm_output: str, ctx: Optional[dict]) -> str:
    if not ctx:
        return f"\n{llm_output.strip()}\n"

    decision = ctx.get("decision", "UNKNOWN")
    icon  = _decision_icon(decision)
    label = _decision_label(decision)

    parts = [
        _header(f"{icon} {label}"),
        _applicant_block(ctx),
        _THIN,
        f"\n  {llm_output.strip()}\n",
        _THICK,
    ]
    return "\n".join(parts)


def _fmt_explanation(llm_output: str, ctx: Optional[dict]) -> str:
    if not ctx:
        return f"\n{llm_output.strip()}\n"

    decision = ctx.get("decision", "UNKNOWN")
    icon  = _decision_icon(decision)
    label = _decision_label(decision)

    parts = [
        _header(f"{icon} {label}"),
        _applicant_block(ctx),
    ]

    # Why section
    parts.append(_section("  WHY THIS DECISION?"))
    # Indent each paragraph
    paragraphs = [p.strip() for p in llm_output.strip().split("\n\n") if p.strip()]
    if paragraphs:
        parts.append("")
        for para in paragraphs:
            # Wrap each paragraph at ~80 chars with 2-space indent
            words = para.split()
            lines_out = []
            cur = "  "
            for w in words:
                if len(cur) + len(w) + 1 > 79:
                    lines_out.append(cur)
                    cur = "  " + w
                else:
                    cur = (cur + " " + w).lstrip()
                    cur = "  " + cur.lstrip()
            lines_out.append(cur)
            parts.append("\n".join(lines_out))
            parts.append("")

    # Key factors
    parts.append(_section("  KEY FACTORS  (what drove this decision)"))
    parts.append("")
    parts.append(_shap_block(ctx))

    # Red flags
    rf = _red_flags_block(ctx)
    if rf:
        parts.append(rf)

    # Loan offer / next steps
    parts.append(_section("  LOAN OFFER / NEXT STEPS"))
    parts.append("")
    parts.append(_loan_offer_block(ctx))
    parts.append(_THICK)

    return "\n".join(parts)


def _fmt_comparison(
    llm_output: str, ctx_a: Optional[dict], ctx_b: Optional[dict]
) -> str:
    parts = [_header("  APPLICANT COMPARISON")]

    if ctx_a and ctx_b:
        n_a  = ctx_a.get("name", "Applicant A")
        n_b  = ctx_b.get("name", "Applicant B")
        g_a  = ctx_a.get("grade", "?")
        g_b  = ctx_b.get("grade", "?")
        pd_a = f"{ctx_a.get('default_probability', 0.0):.1%}"
        pd_b = f"{ctx_b.get('default_probability', 0.0):.1%}"
        d_a  = ctx_a.get("decision", "?")
        d_b  = ctx_b.get("decision", "?")

        col = 22
        parts.append(f"\n  {'':18}  {'A: ' + n_a:<{col}}  B: {n_b}")
        parts.append(f"  {'Grade':18}  {g_a:<{col}}  {g_b}")
        parts.append(f"  {'Default Risk':18}  {pd_a:<{col}}  {pd_b}")
        parts.append(f"  {'Decision':18}  {d_a:<{col}}  {d_b}")

    parts.append(_section("  ANALYST COMPARISON"))
    parts.append(f"\n{llm_output.strip()}\n")
    parts.append(_THICK)
    return "\n".join(parts)


def _fmt_letter(llm_output: str, ctx: Optional[dict]) -> str:
    parts = [_header("  FORMAL CREDIT DECISION LETTER")]
    parts.append("")
    parts.append(llm_output.strip())
    parts.append("")
    parts.append(_THICK)
    return "\n".join(parts)


def _fmt_scenario(llm_output: str, ctx: Optional[dict]) -> str:
    parts = [_header("  SCENARIO ANALYSIS")]
    if ctx:
        parts.append(_applicant_block(ctx))
    parts.append(f"\n  {llm_output.strip()}\n")
    parts.append(_THICK)
    return "\n".join(parts)


def _fmt_risk_assessment(llm_output: str, ctx: Optional[dict]) -> str:
    parts = [_header("  RISK ASSESSMENT")]
    if ctx:
        parts.append(_applicant_block(ctx))
        parts.append(_section("  PRIMARY RISK"))
        parts.append(f"\n  {llm_output.strip()}\n")
        parts.append(_section("  ALL RISK FACTORS"))
        parts.append("")
        parts.append(_shap_block(ctx))
        rf = _red_flags_block(ctx)
        if rf:
            parts.append(rf)
    else:
        parts.append(f"\n{llm_output.strip()}\n")
    parts.append(_THICK)
    return "\n".join(parts)


def _fmt_aggregate(llm_output: str) -> str:
    parts = [
        _header("  PORTFOLIO SUMMARY"),
        f"\n{llm_output.strip()}\n",
        _THICK,
    ]
    return "\n".join(parts)

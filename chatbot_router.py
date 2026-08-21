"""
chatbot_router.py — PDR Credit Analyst Chatbot Query Router
============================================================
Classifies a loan officer's plain-English question into a structured
(query_type, applicant_ids, parameters) tuple for downstream handlers.

Supported query types:
  LOOKUP          — "Pull up applicant ntc_001"
  EXPLANATION     — "Why was this applicant rejected?"
  COMPARISON      — "Compare ntc_001 and ntc_002"
  SCENARIO        — "What if their income increased by 20%?"
  DECISION_LETTER — "Generate a rejection letter for msme_003"
  RISK_ASSESSMENT — "What's the biggest risk for ntc_001?"
  AGGREGATE       — "How many applicants were rejected?"
  UNKNOWN         — Fallback

Usage:
    from chatbot_router import route_query, QueryType, RoutedQuery

    result = route_query("Why was msme_003 flagged as high risk?")
    print(result.query_type)       # QueryType.EXPLANATION
    print(result.applicant_ids)    # ["msme_003"]
    print(result.parameters)       # {"focus": "rejection_reason"}
"""

import re
from dataclasses import dataclass, field
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# QUERY TYPES
# ─────────────────────────────────────────────────────────────────────────────

class QueryType(str, Enum):
    LOOKUP          = "LOOKUP"
    EXPLANATION     = "EXPLANATION"
    COMPARISON      = "COMPARISON"
    SCENARIO        = "SCENARIO"
    DECISION_LETTER = "DECISION_LETTER"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    AGGREGATE       = "AGGREGATE"
    UNKNOWN         = "UNKNOWN"


# ─────────────────────────────────────────────────────────────────────────────
# RETURN TYPE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RoutedQuery:
    """
    Structured output from the query router.

    Attributes:
        query_type    : One of the QueryType enum values.
        applicant_ids : List of extracted applicant IDs (may be empty).
        parameters    : Dict of extra context extracted from the query.
        raw_message   : Original user message (preserved for LLM).
        confidence    : 0.0–1.0 confidence in the classification.
    """
    query_type:    QueryType
    applicant_ids: list[str]         = field(default_factory=list)
    parameters:    dict              = field(default_factory=dict)
    raw_message:   str               = ""
    confidence:    float             = 1.0

    def __str__(self) -> str:
        ids = ", ".join(self.applicant_ids) if self.applicant_ids else "none"
        return (
            f"[{self.query_type.value}] ids=[{ids}] "
            f"params={self.parameters} conf={self.confidence:.2f}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# APPLICANT ID EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

# Matches IDs like: ntc_001, msme_003, app_12345, user-99, NTC001
_ID_PATTERN = re.compile(
    r"\b(?:"
    r"ntc[_\-]?\d{1,4}"           # ntc_001, ntc001, ntc-1
    r"|msme[_\-]?\d{1,4}"         # msme_003, msme003
    r"|app[_\-]?\d{1,6}"          # app_12345
    r"|user[_\-]?\d{1,4}"         # user_99
    r"|[a-z]{2,10}[_\-]\d{1,4}"  # generic: <word>_<number>
    r"|\#\d{3,6}"                  # #4532
    r")\b",
    re.IGNORECASE,
)

def _extract_applicant_ids(text: str) -> list[str]:
    """
    Pull all applicant ID references from free text.
    Normalises #4532 → app_4532, lowercases everything else.
    """
    raw_ids = _ID_PATTERN.findall(text)
    normalised = []
    seen = set()
    for raw in raw_ids:
        # Normalise #1234 → app_1234
        if raw.startswith("#"):
            norm = f"app_{raw[1:]}"
        else:
            norm = raw.lower().replace("-", "_")
        if norm not in seen:
            normalised.append(norm)
            seen.add(norm)
    return normalised


_LOOKUP_VERB_PATTERN = re.compile(
    r"\b(pull.up|fetch|show|get|display|lookup|find|open|give.me|tell.me.about|"
    r"details.for|profile.of|information.on|score.for|summarise)\b",
    re.IGNORECASE,
)

_LOOKUP_FIELD_PATTERN = re.compile(
    r"\b(score|risk.?band|grade|decision|pd|default probability|profile|details|"
    r"top.?factors|top.?contributing.?factors|contributing.?factors)\b",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────────────────────
# KEYWORD SIGNAL TABLES
# Each entry: (regex_pattern, QueryType, parameters_to_set, priority)
# Higher priority = checked first when multiple signals fire.
# ─────────────────────────────────────────────────────────────────────────────

_SIGNALS: list[tuple[re.Pattern, QueryType, dict, int]] = [

    # ── DECISION_LETTER (check before EXPLANATION) ──────────────────────────
    (re.compile(
        r"\b(generate|write|create|draft|produce|make)\b.{0,30}"
        r"\b(letter|rejection letter|approval letter|decision letter|formal letter|notice)\b",
        re.IGNORECASE),
     QueryType.DECISION_LETTER, {"letter_type": "auto"}, 10),

    (re.compile(r"\b(decision|rejection|approval)\s+letter\b", re.IGNORECASE),
     QueryType.DECISION_LETTER, {"letter_type": "auto"}, 10),

    # ── SCENARIO (check before EXPLANATION) ─────────────────────────────────
    (re.compile(
        r"\b(what\s+if|if\s+(they|the\s+applicant|he|she|their)|"
        r"simulate|scenario|hypothetical|suppose|assume|"
        r"increase|decrease|improve|reduce|lower|raise|boost|"
        r"had\s+more|had\s+less|had\s+(no|zero)|change)\b",
        re.IGNORECASE),
     QueryType.SCENARIO, {}, 8),

    # ── COMPARISON ───────────────────────────────────────────────────────────
    (re.compile(
        r"\b(compare|comparison|versus|vs\.?|difference between|"
        r"side.by.side|contrast|how do .+ compare|both)\b",
        re.IGNORECASE),
     QueryType.COMPARISON, {}, 9),

    # ── RISK_ASSESSMENT ──────────────────────────────────────────────────────
    (re.compile(
        r"\b(biggest.?risk|top.?risk|main.?risk|highest.?risk|"
        r"key.?risk|primary.?risk|most.?dangerous|worst.?feature|"
        r"what.?risk|risk.?factor|risk.?profile)\b",
        re.IGNORECASE),
     QueryType.RISK_ASSESSMENT, {}, 7),

    # ── EXPLANATION ──────────────────────────────────────────────────────────
    (re.compile(
        r"\b(why|reason|explain|because|cause|drove|driven|"
        r"what.caused|what.led|flagged|rejected|declined|"
        r"high.risk|key.factor|contributing|behind|rationale)\b",
        re.IGNORECASE),
     QueryType.EXPLANATION, {}, 6),

    # ── AGGREGATE ────────────────────────────────────────────────────────────
    (re.compile(
        r"\b(how.many|count|total|average|avg|all\s+applicants|"
        r"list.all|show.all|distribution|breakdown|summary|"
        r"top\s+\d+|worst\s+\d+|best\s+\d+|"
        r"applicants\s+(with|who|under|over|above|below|between|"
        r"in|from|rejected|approved|reviewed))\b",
        re.IGNORECASE),
     QueryType.AGGREGATE, {}, 5),

    # ── LOOKUP (catch-all where an ID is mentioned) ──────────────────────────
    (re.compile(
        r"\b(pull.up|fetch|show|get|display|lookup|find|open|"
        r"give.me|tell.me.about|details.for|profile.of|"
        r"information.on|score.for|summarise)\b",
        re.IGNORECASE),
     QueryType.LOOKUP, {}, 4),
]


def _detect_scenario_params(text: str) -> dict:
    """
    Extract scenario parameters from the message:
    e.g. "20% more income" → {"feature": "income", "change_type": "increase", "magnitude": 0.20}
    """
    params: dict = {}
    lower = text.lower()

    # Detect percentage change
    pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if pct_match:
        params["magnitude_pct"] = float(pct_match.group(1)) / 100

    # Detect absolute value change
    abs_match = re.search(r"(?:by|to|of)\s+(?:₹|rs\.?|inr)?\s*(\d[\d,]*)", lower)
    if abs_match:
        params["magnitude_abs"] = float(abs_match.group(1).replace(",", ""))

    # Detect direction
    if re.search(r"\b(more|increase|raise|higher|better|improve|boost|up)\b", lower):
        params["change_direction"] = "increase"
    elif re.search(r"\b(less|decrease|lower|reduce|drop|worse|down|no|zero)\b", lower):
        params["change_direction"] = "decrease"

    # Detect which feature is being modified
    feature_keywords = {
        "income":              ["income", "salary", "earnings", "revenue", "turnover"],
        "utility_payment_consistency": ["utility", "bill", "electricity", "water"],
        "bounced_transaction_count":   ["bounce", "bounced", "nsf", "dishonour"],
        "emergency_buffer_months":     ["buffer", "savings", "reserve", "emergency fund"],
        "gst_filing_consistency_score":["gst", "filing", "tax"],
        "cash_withdrawal_dependency":  ["cash", "withdrawal", "atm"],
        "employment_vintage_days":     ["employment", "job", "work", "tenure", "experience"],
        "eod_balance_volatility":      ["balance", "stability", "volatile", "fluctuat"],
        "telecom_number_vintage_days": ["sim", "phone", "telecom", "mobile"],
    }
    for feat, keywords in feature_keywords.items():
        if any(kw in lower for kw in keywords):
            params["target_feature"] = feat
            break

    return params


def _detect_letter_type(text: str) -> str:
    """Returns 'rejection', 'approval', or 'review' based on wording."""
    lower = text.lower()
    if re.search(r"\b(reject|decline|denial|refused)\b", lower):
        return "rejection"
    if re.search(r"\b(approv|accept|sanction)\b", lower):
        return "approval"
    if re.search(r"\b(review|refer|manual|pending)\b", lower):
        return "review"
    return "auto"   # determine from applicant's actual decision


def _detect_aggregate_params(text: str) -> dict:
    """Extract filter hints for aggregate queries."""
    params: dict = {}
    lower = text.lower()

    # Grade filter
    grade_match = re.search(r"\bgrade\s+([a-f][+\-]?)\b", lower)
    if grade_match:
        params["grade"] = grade_match.group(1).upper()

    # Decision filter
    if re.search(r"\b(rejected|declined|rejection)\b", lower):
        params["decision"] = "REJECTED"
    elif re.search(r"\b(approved|approval)\b", lower):
        params["decision"] = "APPROVED"
    elif re.search(r"\b(review|manual|referred)\b", lower):
        params["decision"] = "MANUAL_REVIEW"

    # Age / demographic filters
    age_match = re.search(r"under\s+(\d+)|below\s+(\d+)|over\s+(\d+)|above\s+(\d+)", lower)
    if age_match:
        groups = age_match.groups()
        if groups[0] or groups[1]:
            params["age_filter"] = ("lt", int(groups[0] or groups[1]))
        else:
            params["age_filter"] = ("gt", int(groups[2] or groups[3]))

    # Top-N
    topn_match = re.search(r"\b(top|worst|best)\s+(\d+)\b", lower)
    if topn_match:
        params["limit"] = int(topn_match.group(2))
        params["order"] = topn_match.group(1).lower()

    # Risk band
    if re.search(r"\bhigh.risk\b", lower):
        params["risk_band"] = "HIGH"
    elif re.search(r"\blow.risk\b", lower):
        params["risk_band"] = "LOW"
    elif re.search(r"\bmedium.risk\b", lower):
        params["risk_band"] = "MEDIUM"

    return params


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────────────────────────────────

def route_query(user_message: str) -> RoutedQuery:
    """
    Classify a loan officer's plain-English question into a structured RoutedQuery.

    Args:
        user_message: Raw text from the loan officer.

    Returns:
        RoutedQuery(query_type, applicant_ids, parameters, raw_message, confidence)

    Examples:
        >>> route_query("Pull up applicant ntc_001")
        RoutedQuery(query_type=LOOKUP, applicant_ids=['ntc_001'], ...)

        >>> route_query("Why was msme_003 rejected?")
        RoutedQuery(query_type=EXPLANATION, applicant_ids=['msme_003'], ...)

        >>> route_query("Compare ntc_001 and ntc_002")
        RoutedQuery(query_type=COMPARISON, applicant_ids=['ntc_001','ntc_002'], ...)

        >>> route_query("What if ntc_001 had 20% more income?")
        RoutedQuery(query_type=SCENARIO, ...)

        >>> route_query("Generate a rejection letter for msme_003")
        RoutedQuery(query_type=DECISION_LETTER, ...)

        >>> route_query("What's the biggest risk for ntc_001?")
        RoutedQuery(query_type=RISK_ASSESSMENT, ...)

        >>> route_query("How many applicants were rejected?")
        RoutedQuery(query_type=AGGREGATE, ...)
    """
    if not user_message or not user_message.strip():
        return RoutedQuery(
            query_type=QueryType.UNKNOWN,
            raw_message=user_message,
            confidence=0.0,
            parameters={"error": "Empty query"},
        )

    text = user_message.strip()
    lower = text.lower()

    # ── Step 1: Extract all applicant IDs from message ───────────────────────
    applicant_ids = _extract_applicant_ids(text)

    # ── Step 2: Score all signal patterns ────────────────────────────────────
    fired: list[tuple[int, QueryType, dict]] = []   # (priority, type, params)
    for pattern, qtype, base_params, priority in _SIGNALS:
        if pattern.search(text):
            fired.append((priority, qtype, base_params.copy()))

    # ── Step 3: Pick highest-priority fired signal ────────────────────────────
    if not fired:
        # No keyword matched — if we have an ID, assume LOOKUP
        if applicant_ids:
            return RoutedQuery(
                query_type=QueryType.LOOKUP,
                applicant_ids=applicant_ids,
                raw_message=text,
                confidence=0.6,
                parameters={"fallback": True},
            )
        return RoutedQuery(
            query_type=QueryType.UNKNOWN,
            applicant_ids=applicant_ids,
            raw_message=text,
            confidence=0.0,
            parameters={"hint": "Try asking: 'Pull up ntc_001' or 'How many rejected?'"},
        )

    # Sort by priority descending
    fired.sort(key=lambda x: x[0], reverse=True)
    priority, query_type, parameters = fired[0]

    explicit_lookup_request = (
        bool(applicant_ids)
        and _LOOKUP_VERB_PATTERN.search(text)
        and _LOOKUP_FIELD_PATTERN.search(text)
        and not re.search(r"\b(why|reason|explain|because)\b", lower)
    )
    if explicit_lookup_request:
        query_type = QueryType.LOOKUP
        parameters = {}
        priority = max(priority, 7)

    # ── Step 4: Type-specific parameter extraction ────────────────────────────
    if query_type == QueryType.SCENARIO:
        parameters.update(_detect_scenario_params(text))
        # Detect "what to change to qualify" — no specific feature target identified
        if re.search(
            r"\b(qualify|approve|eligible|what.*(need|change|improve|fix|do))\b",
            lower,
        ) and not parameters.get("target_feature"):
            parameters["focus"] = "improvement_path"

    elif query_type == QueryType.DECISION_LETTER:
        parameters["letter_type"] = _detect_letter_type(text)

    elif query_type == QueryType.AGGREGATE:
        parameters.update(_detect_aggregate_params(text))

    elif query_type == QueryType.COMPARISON and len(applicant_ids) < 2:
        # COMPARISON with only one ID — degrade to LOOKUP with a note
        parameters["comparison_incomplete"] = True
        parameters["hint"] = "Please provide two applicant IDs to compare"

    elif query_type == QueryType.EXPLANATION:
        lower = text.lower()
        if re.search(r"\b(risk|risky|dangerous|concern)\b", lower):
            parameters["focus"] = "risk_factors"
        elif re.search(r"\b(reject|decline|denied|refused|not approved)\b", lower):
            parameters["focus"] = "rejection_reason"
        elif re.search(r"\b(approv|pass|qualify|eligible)\b", lower):
            parameters["focus"] = "approval_reason"
        else:
            parameters["focus"] = "general"

    # ── Step 4b: Extract requested fields for LOOKUP queries ─────────────────
    if query_type == QueryType.LOOKUP and _LOOKUP_FIELD_PATTERN.search(text):
        fields = []
        lower_text = text.lower()
        if "score" in lower_text:
            fields.append("score")
        if "risk" in lower_text:
            fields.append("risk_band")
        if "grade" in lower_text:
            fields.append("grade")
        if "decision" in lower_text:
            fields.append("decision")
        if re.search(r"\bfactor", lower_text):
            fields.append("top_factors")
        if "pd" in lower_text or "default probability" in lower_text or "probability" in lower_text:
            fields.append("pd")
        if fields:
            parameters["fields"] = fields

    # ── Step 5: Confidence calculation ───────────────────────────────────────
    # Higher if: strong keyword matched + IDs found
    confidence = min(1.0, 0.6 + (priority / 25) + (0.15 if applicant_ids else 0.0))

    return RoutedQuery(
        query_type=query_type,
        applicant_ids=applicant_ids,
        parameters=parameters,
        raw_message=text,
        confidence=round(confidence, 2),
    )


# ─────────────────────────────────────────────────────────────────────────────
# QUERY DESCRIPTION — used to build LLM prompts downstream
# ─────────────────────────────────────────────────────────────────────────────

_QUERY_DESCRIPTIONS: dict[QueryType, str] = {
    QueryType.LOOKUP:
        "The loan officer wants a plain-English summary of the applicant's credit profile, "
        "score, and decision.",
    QueryType.EXPLANATION:
        "The loan officer wants to understand WHY the system made a particular decision. "
        "Focus on the top SHAP factors and any pre-layer rules that fired.",
    QueryType.COMPARISON:
        "The loan officer wants a side-by-side comparison of two applicants — highlight "
        "key differences in risk profile, grade, and top features.",
    QueryType.SCENARIO:
        "The loan officer wants to simulate a change to one or more features. "
        "Describe how the change would likely affect the credit decision and which "
        "threshold it would cross.",
    QueryType.DECISION_LETTER:
        "Generate a formal credit decision letter (APPROVED / DECLINED / REFERRED FOR REVIEW) "
        "citing the specific data-driven reasons from the applicant's scoring result.",
    QueryType.RISK_ASSESSMENT:
        "Identify and explain the single biggest risk factor for this applicant, "
        "using the highest-impact SHAP feature and any pre-layer rule triggers.",
    QueryType.AGGREGATE:
        "Answer a portfolio-level question about multiple applicants. "
        "Use aggregate data — counts, averages, distributions — not individual records.",
    QueryType.UNKNOWN:
        "The question could not be classified. Ask the loan officer to rephrase.",
}

def get_query_description(query_type: QueryType) -> str:
    """Return the LLM instruction string for a given query type."""
    return _QUERY_DESCRIPTIONS.get(query_type, _QUERY_DESCRIPTIONS[QueryType.UNKNOWN])


# ─────────────────────────────────────────────────────────────────────────────
# DEMO / QUICK TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        # LOOKUP
        "Pull up applicant ntc_001",
        "Show me the profile for msme_003",
        "Get details for #4532",

        # EXPLANATION
        "Why was msme_003 flagged as high risk?",
        "What's the reason for ntc_002's rejection?",
        "Explain why this applicant was declined",

        # COMPARISON
        "Compare ntc_001 and ntc_002",
        "What's the difference between msme_001 and msme_002?",
        "ntc_001 vs msme_003 — who is riskier?",

        # SCENARIO
        "What if ntc_001 had 20% more income?",
        "If msme_003 had no bounced transactions, would they qualify?",
        "Simulate lower cash withdrawal for ntc_002",

        # DECISION_LETTER
        "Generate a rejection letter for msme_003",
        "Write a formal approval letter for ntc_001",
        "Draft a decision letter for applicant ntc_004",

        # RISK_ASSESSMENT
        "What's the biggest risk for ntc_001?",
        "What is the primary risk factor for msme_002?",

        # AGGREGATE
        "How many applicants were rejected?",
        "Show me the top 5 riskiest applicants",
        "What's the grade distribution across all applicants?",
        "List all high-risk applicants",

        # EDGE CASES
        "hello",                                      # UNKNOWN
        "ntc_001",                                    # LOOKUP (ID only, no verb)
        "Compare ntc_001",                            # COMPARISON with incomplete IDs
    ]

    print(f"{'QUERY':<55} → {'TYPE':<20} {'IDs':<25} PARAMS / CONF")
    print("─" * 120)
    for msg in test_cases:
        r = route_query(msg)
        ids_str = str(r.applicant_ids) if r.applicant_ids else "[]"
        params_str = str(r.parameters) if r.parameters else "{}"
        # Truncate for display
        q_disp = msg[:53] + ".." if len(msg) > 55 else msg
        params_disp = params_str[:35] + ".." if len(params_str) > 37 else params_str
        print(
            f"{q_disp:<55} → {r.query_type.value:<20} {ids_str:<25} "
            f"{params_disp} [{r.confidence:.2f}]"
        )

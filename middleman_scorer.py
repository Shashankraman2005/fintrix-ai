from typing import Dict, Any, Tuple

def get_middleman_thresholds(confidence: str) -> Tuple[float, float]:
    if confidence == "HIGH":
        return (0.35, 0.55)
    elif confidence == "MEDIUM":
        return (0.20, 0.50)
    else:
        return (0.15, 0.45)

def score_middleman_user(
    applicantmetadata: Dict[str, Any],
    supplierdata: Dict[str, Any] = None,
    gstdata: Dict[str, Any] = None,
    telecomdata: Dict[str, Any] = None,
    utilitydata: Dict[str, Any] = None,
    bcagentdata: Dict[str, Any] = None,
) -> Dict[str, Any]:
    sources_used = []
    if supplierdata is not None: sources_used.append("supplier")
    if gstdata is not None: sources_used.append("gst")
    if telecomdata is not None: sources_used.append("telecom")
    if utilitydata is not None: sources_used.append("utility")
    if bcagentdata is not None: sources_used.append("bcagent")

    num_sources = len(sources_used)
    if num_sources >= 4:
        confidence = "HIGH"
    elif num_sources >= 2:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    approve_thresh, review_thresh = get_middleman_thresholds(confidence)

    # Mock probability calculation
    # In a real scenario, extracting features and using a model
    probability_default = 0.25 # Mock default probability

    if probability_default < approve_thresh:
        decision = "APPROVE"
    elif probability_default < review_thresh:
        decision = "MANUAL_REVIEW"
    else:
        decision = "REJECT"

    # Grades mapping mock
    if decision == "APPROVE":
        grade = "A"
    elif decision == "MANUAL_REVIEW":
        grade = "B"
    else:
        grade = "C"

    return {
        "decision": decision,
        "probability_default": probability_default,
        "confidence": confidence,
        "sources_used": sources_used,
        "grade": grade,
        "pre_layer_override": False,
        "top_features": ["business_vintage_months", "utility_payment_consistency", "telecom_number_vintage_days"],
        "feature_vector_valid": True
    }

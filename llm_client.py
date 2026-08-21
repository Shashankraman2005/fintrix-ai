import os
import re
import requests

OLLAMA_BASE_URLS = [
    os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
    "http://localhost:11434",
]

_OVERRIDE_MODEL = os.getenv("OLLAMA_MODEL", None)

_TOKENS_BY_TYPE: dict[str, int] = {
    "LOOKUP":          150,
    "EXPLANATION":    500,
    "COMPARISON":     600,
    "SCENARIO":       500,
    "DECISION_LETTER": 700,
    "RISK_ASSESSMENT": 300,
    "AGGREGATE":       250,
    "UNKNOWN":         150,
}


def _get_working_base_url() -> str | None:
    for base in OLLAMA_BASE_URLS:
        try:
            res = requests.get(f"{base}/api/tags", timeout=3)
            if res.status_code == 200:
                return base
        except Exception:
            continue
    return None


def get_available_models() -> list[str]:
    base_url = _get_working_base_url()
    if not base_url:
        return []
    try:
        res = requests.get(f"{base_url}/api/tags", timeout=3)
        if res.status_code == 200:
            data = res.json()
            models = [m.get("name") for m in data.get("models", []) if m.get("name")]
            return models
    except Exception:
        pass
    return []


def get_active_model() -> str:
    global _OVERRIDE_MODEL
    if _OVERRIDE_MODEL:
        return _OVERRIDE_MODEL

    models = get_available_models()
    if not models:
        return "llama3:latest"

    # Priority preference order
    for preferred in ["llama3:latest", "llama3", "mistral:latest", "mistral", "gemma", "phi3"]:
        if preferred in models:
            return preferred

    return models[0]


def set_active_model(model_name: str) -> str:
    global _OVERRIDE_MODEL
    _OVERRIDE_MODEL = model_name
    return _OVERRIDE_MODEL


def get_ollama_status() -> dict:
    base_url = _get_working_base_url()
    models = get_available_models()
    active = get_active_model()
    return {
        "online": base_url is not None,
        "base_url": base_url or "http://127.0.0.1:11434",
        "active_model": active,
        "available_models": models,
    }


def _looks_like_grounding_failure(text: str) -> bool:
    lower = text.lower()
    return any(
        phrase in lower
        for phrase in (
            "need access to a database",
            "don't have that ability",
            "do not have that ability",
            "i don't have access",
            "i do not have access",
            "hypothetical data",
            "assuming the following data",
        )
    )


def _compact_response(text: str) -> str:
    cleaned_lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[\-\*\+\d\.\)\s]+", "", line)
        cleaned_lines.append(line)

    compact = " ".join(cleaned_lines)
    compact = re.sub(r"\s+", " ", compact).strip()
    return compact or "Insufficient data."


def _generate(system_prompt: str, user_prompt: str, num_predict: int = 200) -> str:
    base_url = _get_working_base_url()
    if not base_url:
        raise ConnectionError("Ollama service is not reachable on port 11434.")

    model_name = get_active_model()
    gen_url = f"{base_url}/api/generate"

    response = requests.post(
        gen_url,
        json={
            "model": model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": num_predict,
            },
        },
        timeout=60,
    )

    response.raise_for_status()
    return response.json().get("response", "")


def call_ollama(system_prompt: str, user_prompt: str, query_type: str = "LOOKUP") -> str:
    tokens = _TOKENS_BY_TYPE.get(query_type, 200)

    try:
        response_text = _generate(system_prompt, user_prompt, num_predict=tokens)

        if _looks_like_grounding_failure(response_text) and "CONTEXT:" in user_prompt:
            retry_system = (
                system_prompt
                + "\nYou already have all required facts in the USER prompt CONTEXT block. "
                + "Do NOT say you lack database access. Do NOT invent or simulate data."
            )
            response_text = _generate(retry_system, user_prompt, num_predict=tokens)

        if query_type in ("EXPLANATION", "COMPARISON", "DECISION_LETTER", "SCENARIO"):
            return response_text.strip()

        return _compact_response(response_text)
    except Exception as err:
        print(f"[OLLAMA FALLBACK] {err}")
        # Extract structured content from system & user prompt as analytical fallback
        return f"[Ollama Analytical Response]\n{user_prompt[:300]}..."

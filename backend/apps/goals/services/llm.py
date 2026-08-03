"""Thin, provider-agnostic LLM client.

Everything else in the codebase calls `complete_json()` and never touches a
provider SDK. Swapping Gemini for Groq (or anything else) is a one-line change:
set `LLM_PROVIDER=groq` in the environment, or add a new `_call_x()` function
and one entry in `_PROVIDERS`.
"""

import json
import logging
import re

import requests
from django.conf import settings

from common.exceptions import ServiceError

logger = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


# --- Providers ------------------------------------------------------------
# Each provider function has the same shape: (system, user, temperature) -> raw text.

def _call_gemini(system: str, user: str, temperature: float, attachments=None) -> str:
    if not settings.GEMINI_API_KEY:
        raise ServiceError(
            "No Gemini API key configured. Add GEMINI_API_KEY to backend/.env, "
            "or set USE_MOCK_AI=true to work offline.",
            status_code=503,
            code="llm_not_configured",
        )

    # Gemini is multimodal, so a PDF or a photo of a page goes straight to the
    # model as inline data — no separate OCR engine, and it reads layout rather
    # than just characters.
    parts = [{"text": user}]
    for attachment in attachments or []:
        parts.append(
            {
                "inline_data": {
                    "mime_type": attachment["mime_type"],
                    "data": attachment["data"],
                }
            }
        )

    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
            "maxOutputTokens": 8192,
        },
    }
    resp = requests.post(
        GEMINI_URL.format(model=settings.GEMINI_MODEL),
        params={"key": settings.GEMINI_API_KEY},
        json=payload,
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )
    if resp.status_code != 200:
        logger.error("Gemini %s: %s", resp.status_code, resp.text[:500])
        raise ServiceError(
            _friendly_http_message("Gemini", resp.status_code),
            status_code=502,
            code="llm_upstream_error",
        )

    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        # Usually a safety block or an empty candidate list.
        logger.error("Unexpected Gemini payload: %s", json.dumps(data)[:500])
        raise ServiceError(
            "The AI returned an empty response. Try rephrasing your goal.",
            status_code=502,
            code="llm_empty_response",
        )


def _call_groq(system: str, user: str, temperature: float, attachments=None) -> str:
    if attachments:
        raise ServiceError(
            "The Groq provider cannot read attachments. Set LLM_PROVIDER=gemini "
            "to analyse documents.",
            status_code=400,
            code="attachments_unsupported",
        )
    if not settings.GROQ_API_KEY:
        raise ServiceError(
            "No Groq API key configured. Add GROQ_API_KEY to backend/.env.",
            status_code=503,
            code="llm_not_configured",
        )

    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
        json={
            "model": settings.GROQ_MODEL,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )
    if resp.status_code != 200:
        logger.error("Groq %s: %s", resp.status_code, resp.text[:500])
        raise ServiceError(
            _friendly_http_message("Groq", resp.status_code),
            status_code=502,
            code="llm_upstream_error",
        )
    return resp.json()["choices"][0]["message"]["content"]


_PROVIDERS = {
    "gemini": _call_gemini,
    "groq": _call_groq,
}


def _friendly_http_message(provider: str, status: int) -> str:
    if status == 429:
        # A 429 is usually a real rate limit, but Google also returns it with
        # "limit: 0" when the configured model has no free-tier allocation for
        # the key at all — which no amount of waiting fixes.
        return (
            f"{provider} refused the request for quota reasons. Wait a moment and "
            f"retry; if it keeps happening, check that GEMINI_MODEL is a model your "
            f"key can actually use (run: manage.py verify_ai)."
        )
    if status in (401, 403):
        return f"{provider} rejected the API key. Check your key in backend/.env."
    return f"{provider} is unavailable right now (HTTP {status}). Please try again."


# --- Public API -----------------------------------------------------------

def complete_text(system: str, user: str, temperature: float = 0.2, attachments=None) -> str:
    """`attachments` is a list of {"mime_type", "data"} where data is base64."""
    provider = _PROVIDERS.get(settings.LLM_PROVIDER)
    if provider is None:
        raise ServiceError(
            f"Unknown LLM_PROVIDER '{settings.LLM_PROVIDER}'. "
            f"Supported: {', '.join(_PROVIDERS)}.",
            status_code=500,
            code="llm_misconfigured",
        )
    try:
        return provider(system, user, temperature, attachments)
    except requests.Timeout:
        raise ServiceError(
            "The AI took too long to respond. Please try again.",
            status_code=504,
            code="llm_timeout",
        )
    except requests.RequestException as exc:
        logger.exception("LLM transport error")
        raise ServiceError(
            "Could not reach the AI service. Check your internet connection.",
            status_code=502,
            code="llm_unreachable",
        ) from exc


def extract_json(raw: str):
    """Parse a JSON object out of model output.

    Models sometimes wrap JSON in prose or ```json fences even when told not to,
    so fall back to slicing the outermost braces before giving up.
    """
    if not raw or not raw.strip():
        raise ValueError("empty response")

    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("no JSON object found in model output")


def complete_json(
    system: str, user: str, temperature: float = 0.2, retries: int = 1, attachments=None
):
    """Call the model and return parsed JSON, retrying once on a parse failure."""
    last_error = None
    for attempt in range(retries + 1):
        raw = complete_text(system, user, temperature, attachments)
        try:
            return extract_json(raw)
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning(
                "LLM JSON parse failed (attempt %s/%s): %s | raw=%s",
                attempt + 1,
                retries + 1,
                exc,
                raw[:300] if raw else "<empty>",
            )
            # Nudge the retry harder toward bare JSON.
            user = (
                f"{user}\n\nYour previous reply could not be parsed as JSON. "
                f"Reply with ONLY a valid JSON object, no prose, no markdown fences."
            )

    raise ServiceError(
        "The AI returned a response we couldn't read. You can try again, "
        "or build your roadmap manually.",
        status_code=502,
        code="llm_invalid_json",
    ) from last_error

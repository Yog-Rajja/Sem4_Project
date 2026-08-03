"""Thin, provider-agnostic LLM client with automatic fallback.

Everything else in the codebase calls `complete_json()` and never touches a
provider SDK.

The client walks a **chain** of `provider:model` entries in order. When one is
exhausted (429), retired (404) or overloaded (503) it moves to the next rather
than surfacing an error — so a dead model or a spent daily quota degrades into
a slightly different answer instead of a broken feature.

Configure with LLM_FALLBACK_CHAIN, e.g.

    LLM_FALLBACK_CHAIN=gemini:gemini-3.5-flash,gemini:gemini-flash-lite-latest,groq:llama-3.3-70b-versatile

Note that **Groq and Grok are different companies**: Groq (api.groq.com) sells
fast inference of open models; Grok is xAI's model family (api.x.ai). Both are
supported, under the names `groq` and `xai`.
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
XAI_URL = "https://api.x.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Statuses where a different model or provider is worth trying.
RETRYABLE_STATUSES = {404, 408, 409, 429, 500, 502, 503, 504}


class ProviderError(Exception):
    """Internal: one link in the chain failed. Carries whether to move on."""

    def __init__(self, message, *, retryable: bool, status: int | None = None):
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.status = status


# --- providers ------------------------------------------------------------
# Each returns raw text, or raises ProviderError.

def _call_gemini(model, system, user, temperature, attachments):
    key = settings.GEMINI_API_KEY
    if not key:
        raise ProviderError("no GEMINI_API_KEY", retryable=True)

    parts = [{"text": user}]
    for attachment in attachments or []:
        parts.append(
            {"inline_data": {"mime_type": attachment["mime_type"],
                             "data": attachment["data"]}}
        )

    response = requests.post(
        GEMINI_URL.format(model=model),
        params={"key": key},
        json={
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
                "maxOutputTokens": 8192,
            },
        },
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        raise ProviderError(
            _short_error(response),
            retryable=response.status_code in RETRYABLE_STATUSES,
            status=response.status_code,
        )

    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        # Usually a safety block or an empty candidate list.
        raise ProviderError("empty response", retryable=True)


def _openai_compatible(url, key, model, system, user, temperature, attachments,
                       extra_headers=None):
    """Groq, xAI and OpenRouter all speak the OpenAI chat format."""
    if not key:
        raise ProviderError(f"no API key for {url}", retryable=True)
    if attachments:
        raise ProviderError("provider cannot read attachments", retryable=True)

    headers = {"Authorization": f"Bearer {key}"}
    headers.update(extra_headers or {})

    response = requests.post(
        url,
        headers=headers,
        json={
            "model": model,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        raise ProviderError(
            _short_error(response),
            retryable=response.status_code in RETRYABLE_STATUSES,
            status=response.status_code,
        )
    try:
        return response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise ProviderError("empty response", retryable=True)


def _call_groq(model, system, user, temperature, attachments):
    return _openai_compatible(
        GROQ_URL, settings.GROQ_API_KEY, model, system, user, temperature, attachments
    )


def _call_xai(model, system, user, temperature, attachments):
    return _openai_compatible(
        XAI_URL, settings.XAI_API_KEY, model, system, user, temperature, attachments
    )


def _call_openrouter(model, system, user, temperature, attachments):
    return _openai_compatible(
        OPENROUTER_URL,
        settings.OPENROUTER_API_KEY,
        model, system, user, temperature, attachments,
        extra_headers={
            "HTTP-Referer": settings.APP_BASE_URL,
            "X-Title": "Smart Companion",
        },
    )


PROVIDERS = {
    "gemini": _call_gemini,
    "groq": _call_groq,     # api.groq.com — fast inference of open models
    "xai": _call_xai,       # api.x.ai — Grok
    "openrouter": _call_openrouter,
}

# Which providers can be handed a PDF or an image.
MULTIMODAL_PROVIDERS = {"gemini"}


def _short_error(response) -> str:
    try:
        message = response.json().get("error", {})
        if isinstance(message, dict):
            message = message.get("message", "")
        return f"HTTP {response.status_code}: {str(message).splitlines()[0][:150]}"
    except Exception:
        return f"HTTP {response.status_code}: {response.text[:120]}"


# --- the chain ------------------------------------------------------------

def resolve_chain(*, needs_attachments: bool = False) -> list[tuple[str, str]]:
    """Parse LLM_FALLBACK_CHAIN into [(provider, model), …].

    Entries for unknown providers, or ones with no API key, are dropped here
    rather than wasting a request to discover it.
    """
    raw = settings.LLM_FALLBACK_CHAIN.strip()
    if not raw:
        raw = f"{settings.LLM_PROVIDER}:{settings.GEMINI_MODEL}"

    keys = {
        "gemini": settings.GEMINI_API_KEY,
        "groq": settings.GROQ_API_KEY,
        "xai": settings.XAI_API_KEY,
        "openrouter": settings.OPENROUTER_API_KEY,
    }

    chain = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        provider, _, model = entry.partition(":")
        provider, model = provider.strip().lower(), model.strip()
        if provider not in PROVIDERS or not model:
            logger.warning("Ignoring unusable chain entry %r", entry)
            continue
        if not keys.get(provider):
            continue
        if needs_attachments and provider not in MULTIMODAL_PROVIDERS:
            continue
        chain.append((provider, model))
    return chain


def complete_text(system: str, user: str, temperature: float = 0.2, attachments=None) -> str:
    """Try each link in the chain until one answers."""
    chain = resolve_chain(needs_attachments=bool(attachments))

    if not chain:
        raise ServiceError(
            "No usable AI model is configured. Add an API key to backend/.env "
            "(GEMINI_API_KEY, GROQ_API_KEY, XAI_API_KEY or OPENROUTER_API_KEY) "
            "and check LLM_FALLBACK_CHAIN."
            + (
                " Note that reading documents needs Gemini specifically."
                if attachments
                else ""
            ),
            status_code=503,
            code="llm_not_configured",
        )

    attempts = []
    for index, (provider, model) in enumerate(chain):
        try:
            text = PROVIDERS[provider](model, system, user, temperature, attachments)
            if index:
                logger.info("Fell back to %s:%s after %s", provider, model, attempts)
            return text
        except ProviderError as exc:
            attempts.append(f"{provider}:{model} ({exc.message})")
            if not exc.retryable:
                # A bad key or a rejected prompt won't improve on the next
                # model from the same family, but another provider might.
                logger.warning("Non-retryable failure on %s:%s — %s",
                               provider, model, exc.message)
            continue
        except requests.Timeout:
            attempts.append(f"{provider}:{model} (timeout)")
            continue
        except requests.RequestException as exc:
            attempts.append(f"{provider}:{model} (unreachable)")
            logger.warning("Transport error on %s:%s: %s", provider, model, exc)
            continue

    logger.error("Every model in the chain failed: %s", "; ".join(attempts))
    raise ServiceError(
        "Every configured AI model is currently unavailable — most likely the "
        "free daily quota is spent. Add another provider key to backend/.env "
        "(GROQ_API_KEY or OPENROUTER_API_KEY), or try again tomorrow. "
        "Run `manage.py check_llm` to see which models still respond.",
        status_code=503,
        code="llm_all_exhausted",
    )


# --- JSON handling --------------------------------------------------------

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

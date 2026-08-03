"""Raster image generation.

Kept behind the same thin-client idea as the text model: everything else calls
`generate_image()` and never touches a provider SDK.

Note on availability — Gemini's image models appear in the model list for every
key but return 429 with no quota allocation on the free tier, and keep doing so
after the retry window. Image generation is a paid feature. The code below is
correct and will work the moment billing is enabled; until then the user gets a
clear explanation rather than a silent failure.
"""

import base64
import logging

import requests
from django.conf import settings

from common.exceptions import ServiceError

logger = logging.getLogger(__name__)

GEMINI_IMAGE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

SAFE_SUFFIX = (
    " Do not render any text, words, letters or numbers in the image. "
    "Do not depict real company, political or institutional logos."
)


def _friendly_failure(status: int, message: str) -> ServiceError:
    if status == 429:
        return ServiceError(
            "Image generation isn't included in the Gemini free tier — the "
            "model accepts the request but has no free quota, so it returns a "
            "quota error however long you wait. Enable billing on your Google "
            "AI Studio project to switch it on. In the meantime, an Invitation "
            "card gives you a designed, downloadable result for free.",
            status_code=402,
            code="image_generation_unavailable",
        )
    if status in (401, 403):
        return ServiceError(
            "Gemini rejected the API key for image generation.",
            status_code=502,
            code="image_auth_failed",
        )
    if status == 404:
        return ServiceError(
            f"The image model '{settings.GEMINI_IMAGE_MODEL}' isn't available "
            f"to this key. Try another in GEMINI_IMAGE_MODEL.",
            status_code=502,
            code="image_model_unavailable",
        )
    logger.error("Image generation failed %s: %s", status, message[:400])
    return ServiceError(
        f"Could not generate the image (HTTP {status}).",
        status_code=502,
        code="image_generation_failed",
    )


def generate_image(prompt: str) -> tuple[bytes, str]:
    """Return (image_bytes, mime_type). Raises ServiceError with a readable
    explanation on any failure."""
    if not settings.GEMINI_API_KEY:
        raise ServiceError(
            "No Gemini API key configured.",
            status_code=503,
            code="llm_not_configured",
        )

    model = settings.GEMINI_IMAGE_MODEL
    try:
        response = requests.post(
            GEMINI_IMAGE_URL.format(model=model),
            params={"key": settings.GEMINI_API_KEY},
            json={
                "contents": [{"role": "user", "parts": [{"text": prompt + SAFE_SUFFIX}]}],
                "generationConfig": {"responseModalities": ["IMAGE"]},
            },
            timeout=settings.LLM_TIMEOUT_SECONDS * 3,
        )
    except requests.Timeout:
        raise ServiceError(
            "The image took too long to generate. Please try again.",
            status_code=504,
            code="image_timeout",
        )
    except requests.RequestException as exc:
        raise ServiceError(
            "Could not reach the image service.",
            status_code=502,
            code="image_unreachable",
        ) from exc

    if response.status_code != 200:
        raise _friendly_failure(response.status_code, response.text)

    try:
        parts = response.json()["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError):
        raise ServiceError(
            "The image model returned nothing usable. Try rephrasing.",
            status_code=502,
            code="image_empty_response",
        )

    for part in parts:
        blob = part.get("inlineData") or part.get("inline_data")
        if blob and blob.get("data"):
            return base64.b64decode(blob["data"]), blob.get("mimeType", "image/png")

    # A refusal comes back as text rather than pixels.
    refusal = next((p.get("text") for p in parts if p.get("text")), "")
    raise ServiceError(
        refusal.strip()[:300]
        or "The image model declined that request. Try describing it differently.",
        status_code=422,
        code="image_declined",
    )

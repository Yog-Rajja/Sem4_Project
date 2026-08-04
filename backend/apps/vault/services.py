"""Document intelligence: read an uploaded file and make sense of it.

Text-bearing PDFs are extracted locally with pypdf, which is free and exact.
Only scanned pages and photographs fall through to Gemini's multimodal
reading — which also means there is no OCR engine to install.
"""

import base64
import io
import logging
import os

from django.conf import settings
from django.utils import timezone

from common.exceptions import ServiceError

from apps.goals.services import llm

logger = logging.getLogger(__name__)

# Below this, a PDF is almost certainly scanned rather than text-bearing.
MIN_USEFUL_CHARS = 250
MAX_VISION_BYTES = 10 * 1024 * 1024
MAX_STORED_CHARS = 60_000

PLAIN_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log", ".rtf"}
IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}

ANALYSE_SYSTEM_PROMPT = """\
You read a document and explain what it is and what matters in it.

Reply with ONLY a JSON object. No prose, no markdown fences.

{
  "doc_type": "string - 1 to 3 words, e.g. 'Syllabus', 'Job description', \
'Lecture notes', 'Marksheet', 'Research paper'",
  "summary": "string - 3 to 5 sentences describing what this document is and \
what it contains",
  "key_points": ["string - the specific facts that matter, 5 to 10 of them"],
  "suggested_actions": ["string - 2 to 4 things the reader could usefully do \
next, phrased as imperatives"],
  "extracted_text": "string - the readable text content of the document, \
plain text, preserving headings and list order. Empty string if the text was \
already supplied to you."
}

Rules:
- Report only what the document actually says. Never infer facts that are not \
present, and never fill a gap with something plausible.
- key_points should be concrete: dates, module names, requirements, marks, \
deadlines. Not "the document discusses several topics".
- suggested_actions must relate to this specific document. Good: "Create a \
revision goal for the five units listed". Bad: "Read the document carefully".
- If the document is unreadable, say so in the summary and return empty lists.
- Never use an em dash anywhere in your reply.
"""


def _read_bytes(document) -> bytes:
    document.file.open("rb")
    try:
        return document.file.read()
    finally:
        document.file.close()


def _extract_pdf_text(raw: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        chunks = []
        for page in reader.pages[:40]:
            try:
                chunks.append(page.extract_text() or "")
            except Exception:  # a single malformed page shouldn't lose the rest
                continue
        return "\n\n".join(chunk.strip() for chunk in chunks if chunk.strip())
    except Exception:
        logger.exception("pypdf could not read the document")
        return ""


def prepare(document) -> tuple[str, dict | None]:
    """Return (local_text, attachment) — at most one will be meaningful."""
    name = (document.original_name or document.file.name or "").lower()
    extension = os.path.splitext(name)[1]
    raw = _read_bytes(document)

    if extension in PLAIN_EXTENSIONS:
        return raw.decode("utf-8", errors="replace")[:MAX_STORED_CHARS], None

    if extension == ".pdf":
        text = _extract_pdf_text(raw)
        if len(text) >= MIN_USEFUL_CHARS:
            return text[:MAX_STORED_CHARS], None
        # Scanned: hand the whole PDF to the model to read visually.
        if len(raw) <= MAX_VISION_BYTES:
            return "", {
                "mime_type": "application/pdf",
                "data": base64.b64encode(raw).decode(),
            }
        raise ServiceError(
            "This PDF has no selectable text and is too large to read visually. "
            "Try a smaller file.",
            status_code=400,
            code="document_too_large",
        )

    if extension in IMAGE_MIME:
        if len(raw) > MAX_VISION_BYTES:
            raise ServiceError(
                "That image is too large to analyse. Try one under 10 MB.",
                status_code=400,
                code="document_too_large",
            )
        return "", {
            "mime_type": IMAGE_MIME[extension],
            "data": base64.b64encode(raw).decode(),
        }

    # Unknown type: try it as text before giving up.
    decoded = raw.decode("utf-8", errors="replace").strip()
    if len(decoded) >= MIN_USEFUL_CHARS:
        return decoded[:MAX_STORED_CHARS], None

    raise ServiceError(
        "We can't read that file type yet. PDFs, images and text files work.",
        status_code=400,
        code="unsupported_document",
    )


def _mock_analysis(document, local_text):
    return {
        "doc_type": "Document",
        "summary": (
            f"Offline stub for “{document.original_name}”. "
            f"Set USE_MOCK_AI=false to read the real contents."
        ),
        "key_points": ["Stub key point one", "Stub key point two"],
        "suggested_actions": ["Create a goal from this document"],
        "extracted_text": local_text,
    }


def analyse(document) -> dict:
    """Read the document, store what we learned, and return it."""
    local_text, attachment = prepare(document)

    if settings.USE_MOCK_AI:
        payload = _mock_analysis(document, local_text)
    else:
        if attachment:
            user_prompt = (
                f"Filename: {document.original_name}\n\n"
                f"Read the attached document and return the JSON."
            )
        else:
            user_prompt = (
                f"Filename: {document.original_name}\n\n"
                f"Document text:\n\n{local_text[:20000]}\n\n"
                f"Return the JSON. `extracted_text` may be an empty string "
                f"since the text is already above."
            )

        payload = llm.complete_json(
            system=ANALYSE_SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.2,
            attachments=[attachment] if attachment else None,
        )

    if not isinstance(payload, dict):
        raise ServiceError(
            "The AI response was not in the expected format.",
            status_code=502,
            code="schema_invalid",
        )

    def clean_list(value, cap=12):
        if not isinstance(value, list):
            return []
        out = [str(item).strip()[:400] for item in value[:cap] if str(item).strip()]
        return out

    model_text = payload.get("extracted_text")
    text = local_text or (
        model_text.strip()[:MAX_STORED_CHARS] if isinstance(model_text, str) else ""
    )

    document.extracted_text = text
    document.summary = str(payload.get("summary") or "").strip()[:4000]
    document.doc_type = str(payload.get("doc_type") or "").strip()[:60]
    document.key_points = clean_list(payload.get("key_points"))
    document.suggested_actions = clean_list(payload.get("suggested_actions"), 6)
    document.analysed_at = timezone.now()
    document.save(
        update_fields=[
            "extracted_text", "summary", "doc_type",
            "key_points", "suggested_actions", "analysed_at",
        ]
    )
    return document

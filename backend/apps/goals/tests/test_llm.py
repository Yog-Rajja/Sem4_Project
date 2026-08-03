import datetime as dt
import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from common.exceptions import ServiceError

from apps.goals.services import llm


class ExtractJsonTests(SimpleTestCase):
    """Models ignore "JSON only" often enough that parsing has to be forgiving."""

    def test_parses_plain_json(self):
        self.assertEqual(llm.extract_json('{"a": 1}'), {"a": 1})

    def test_parses_json_inside_markdown_fences(self):
        raw = '```json\n{"milestones": []}\n```'
        self.assertEqual(llm.extract_json(raw), {"milestones": []})

    def test_parses_json_inside_bare_fences(self):
        self.assertEqual(llm.extract_json('```\n{"a": 2}\n```'), {"a": 2})

    def test_parses_json_wrapped_in_prose(self):
        raw = 'Sure! Here is your plan:\n{"a": 3}\nHope that helps.'
        self.assertEqual(llm.extract_json(raw), {"a": 3})

    def test_empty_response_raises(self):
        with self.assertRaises(ValueError):
            llm.extract_json("   ")

    def test_response_without_json_raises(self):
        with self.assertRaises(ValueError):
            llm.extract_json("I cannot help with that.")


@override_settings(
    LLM_FALLBACK_CHAIN="gemini:test-model",
    GEMINI_API_KEY="test-key",
    GROQ_API_KEY="", XAI_API_KEY="", OPENROUTER_API_KEY="",
)
class CompleteJsonRetryTests(SimpleTestCase):
    def test_retries_once_then_succeeds(self):
        with patch.object(
            llm, "complete_text", side_effect=["not json at all", '{"ok": true}']
        ) as mocked:
            result = llm.complete_json("sys", "user")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(mocked.call_count, 2)

    def test_second_prompt_pushes_harder_for_bare_json(self):
        with patch.object(
            llm, "complete_text", side_effect=["nope", '{"ok": 1}']
        ) as mocked:
            llm.complete_json("sys", "original prompt")
        retry_prompt = mocked.call_args_list[1].kwargs.get("user") or mocked.call_args_list[1][0][1]
        self.assertIn("ONLY a valid JSON object", retry_prompt)

    def test_gives_up_with_a_clear_error(self):
        with patch.object(llm, "complete_text", return_value="still not json"):
            with self.assertRaises(ServiceError) as ctx:
                llm.complete_json("sys", "user")
        self.assertEqual(ctx.exception.code, "llm_invalid_json")
        # The message must tell the user they can fall back to manual entry.
        self.assertIn("manually", ctx.exception.detail)


@override_settings(
    GEMINI_API_KEY="", GROQ_API_KEY="", XAI_API_KEY="", OPENROUTER_API_KEY=""
)
class ProviderConfigTests(SimpleTestCase):
    def test_missing_api_key_is_reported_as_configuration_error(self):
        with self.assertRaises(ServiceError) as ctx:
            llm.complete_text("sys", "user")
        self.assertEqual(ctx.exception.code, "llm_not_configured")
        self.assertEqual(ctx.exception.status_code, 503)

    @override_settings(LLM_FALLBACK_CHAIN="nonsense:whatever")
    def test_an_unknown_provider_leaves_nothing_usable(self):
        """Unknown providers are dropped when the chain is parsed, so this
        surfaces as "nothing configured" rather than a separate error."""
        with self.assertRaises(ServiceError) as ctx:
            llm.complete_text("sys", "user")
        self.assertEqual(ctx.exception.code, "llm_not_configured")


@override_settings(
    LLM_FALLBACK_CHAIN="gemini:test-model",
    GEMINI_API_KEY="test-key",
    GROQ_API_KEY="", XAI_API_KEY="", OPENROUTER_API_KEY="",
)
class GeminiTransportTests(SimpleTestCase):
    """A single-entry chain, so upstream failures surface directly rather than
    being masked by a fallback."""

    def _response(self, status, payload):
        class FakeResponse:
            status_code = status
            text = json.dumps(payload)

            def json(self):
                return payload

        return FakeResponse()

    def test_reads_text_out_of_a_successful_response(self):
        payload = {"candidates": [{"content": {"parts": [{"text": '{"a": 1}'}]}}]}
        with patch.object(llm.requests, "post", return_value=self._response(200, payload)):
            self.assertEqual(llm.complete_text("sys", "user"), '{"a": 1}')

    def test_a_quota_refusal_exhausts_the_chain(self):
        with patch.object(llm.requests, "post", return_value=self._response(429, {})):
            with self.assertRaises(ServiceError) as ctx:
                llm.complete_text("sys", "user")
        self.assertEqual(ctx.exception.code, "llm_all_exhausted")
        self.assertIn("quota", ctx.exception.detail.lower())

    def test_a_rejected_key_exhausts_the_chain(self):
        with patch.object(llm.requests, "post", return_value=self._response(403, {})):
            with self.assertRaises(ServiceError) as ctx:
                llm.complete_text("sys", "user")
        self.assertEqual(ctx.exception.code, "llm_all_exhausted")

    def test_empty_candidate_list_is_handled(self):
        with patch.object(
            llm.requests, "post", return_value=self._response(200, {"candidates": []})
        ):
            with self.assertRaises(ServiceError) as ctx:
                llm.complete_text("sys", "user")
        self.assertEqual(ctx.exception.code, "llm_all_exhausted")

    def test_a_timeout_exhausts_a_single_entry_chain(self):
        with patch.object(llm.requests, "post", side_effect=llm.requests.Timeout()):
            with self.assertRaises(ServiceError) as ctx:
                llm.complete_text("sys", "user")
        self.assertEqual(ctx.exception.code, "llm_all_exhausted")

    def test_attachments_are_sent_as_inline_data(self):
        payload = {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}
        with patch.object(
            llm.requests, "post", return_value=self._response(200, payload)
        ) as posted:
            llm.complete_text(
                "sys", "user",
                attachments=[{"mime_type": "application/pdf", "data": "BASE64"}],
            )
        parts = posted.call_args.kwargs["json"]["contents"][0]["parts"]
        self.assertEqual(parts[1]["inline_data"]["mime_type"], "application/pdf")

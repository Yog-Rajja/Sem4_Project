from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from common.exceptions import ServiceError

from apps.goals.services import llm

KEYS = {
    "GEMINI_API_KEY": "gem-key",
    "GROQ_API_KEY": "groq-key",
    "XAI_API_KEY": "xai-key",
    "OPENROUTER_API_KEY": "or-key",
}


def fail(message, *, retryable=True, status=None):
    return llm.ProviderError(message, retryable=retryable, status=status)


@override_settings(**KEYS)
class ChainResolutionTests(SimpleTestCase):
    @override_settings(LLM_FALLBACK_CHAIN="gemini:a,groq:b,xai:c")
    def test_entries_are_parsed_in_order(self):
        self.assertEqual(
            llm.resolve_chain(), [("gemini", "a"), ("groq", "b"), ("xai", "c")]
        )

    @override_settings(LLM_FALLBACK_CHAIN="gemini:a,groq:b", GROQ_API_KEY="")
    def test_providers_without_a_key_are_dropped(self):
        """Listing a provider you haven't signed up for should cost nothing."""
        self.assertEqual(llm.resolve_chain(), [("gemini", "a")])

    @override_settings(LLM_FALLBACK_CHAIN="gemini:a,nonsense:b,gemini:")
    def test_unusable_entries_are_ignored(self):
        self.assertEqual(llm.resolve_chain(), [("gemini", "a")])

    @override_settings(LLM_FALLBACK_CHAIN="groq:b,gemini:a,xai:c")
    def test_attachments_narrow_the_chain_to_multimodal_providers(self):
        self.assertEqual(
            llm.resolve_chain(needs_attachments=True), [("gemini", "a")]
        )

    @override_settings(LLM_FALLBACK_CHAIN="", LLM_PROVIDER="gemini", GEMINI_MODEL="solo")
    def test_an_empty_chain_falls_back_to_the_single_model_settings(self):
        self.assertEqual(llm.resolve_chain(), [("gemini", "solo")])

    @override_settings(LLM_FALLBACK_CHAIN="  gemini:a ,, groq:b  ")
    def test_whitespace_and_blanks_are_tolerated(self):
        self.assertEqual(llm.resolve_chain(), [("gemini", "a"), ("groq", "b")])


@override_settings(**KEYS)
class FallbackBehaviourTests(SimpleTestCase):
    @override_settings(LLM_FALLBACK_CHAIN="gemini:first,gemini:second")
    def test_the_first_working_model_is_used(self):
        with patch.dict(llm.PROVIDERS, {"gemini": lambda m, *a: f"from {m}"}):
            self.assertEqual(llm.complete_text("s", "u"), "from first")

    @override_settings(LLM_FALLBACK_CHAIN="gemini:spent,gemini:fresh")
    def test_an_exhausted_model_falls_through_to_the_next(self):
        """The whole point: a spent daily quota must not break the feature."""
        def provider(model, *args):
            if model == "spent":
                raise fail("HTTP 429: quota", status=429)
            return "from fresh"

        with patch.dict(llm.PROVIDERS, {"gemini": provider}):
            self.assertEqual(llm.complete_text("s", "u"), "from fresh")

    @override_settings(LLM_FALLBACK_CHAIN="gemini:retired,gemini:live")
    def test_a_retired_model_falls_through(self):
        def provider(model, *args):
            if model == "retired":
                raise fail("HTTP 404: no longer available", status=404)
            return "from live"

        with patch.dict(llm.PROVIDERS, {"gemini": provider}):
            self.assertEqual(llm.complete_text("s", "u"), "from live")

    @override_settings(LLM_FALLBACK_CHAIN="gemini:a,groq:b")
    def test_it_crosses_providers_not_just_models(self):
        def gemini(model, *args):
            raise fail("HTTP 429: quota", status=429)

        with patch.dict(
            llm.PROVIDERS, {"gemini": gemini, "groq": lambda m, *a: "from groq"}
        ):
            self.assertEqual(llm.complete_text("s", "u"), "from groq")

    @override_settings(LLM_FALLBACK_CHAIN="gemini:a,groq:b")
    def test_a_rejected_key_still_lets_another_provider_answer(self):
        def gemini(model, *args):
            raise fail("HTTP 401: bad key", retryable=False, status=401)

        with patch.dict(
            llm.PROVIDERS, {"gemini": gemini, "groq": lambda m, *a: "from groq"}
        ):
            self.assertEqual(llm.complete_text("s", "u"), "from groq")

    @override_settings(LLM_FALLBACK_CHAIN="gemini:a,groq:b")
    def test_a_timeout_moves_on(self):
        import requests

        def gemini(model, *args):
            raise requests.Timeout()

        with patch.dict(
            llm.PROVIDERS, {"gemini": gemini, "groq": lambda m, *a: "from groq"}
        ):
            self.assertEqual(llm.complete_text("s", "u"), "from groq")

    @override_settings(LLM_FALLBACK_CHAIN="gemini:a,groq:b")
    def test_exhausting_everything_is_explained_clearly(self):
        def dead(model, *args):
            raise fail("HTTP 429: quota", status=429)

        with patch.dict(llm.PROVIDERS, {"gemini": dead, "groq": dead}):
            with self.assertRaises(ServiceError) as ctx:
                llm.complete_text("s", "u")

        self.assertEqual(ctx.exception.code, "llm_all_exhausted")
        self.assertIn("GROQ_API_KEY", ctx.exception.detail)

    @override_settings(
        LLM_FALLBACK_CHAIN="gemini:a", GEMINI_API_KEY="", GROQ_API_KEY="",
        XAI_API_KEY="", OPENROUTER_API_KEY="",
    )
    def test_no_keys_at_all_is_reported_as_configuration(self):
        with self.assertRaises(ServiceError) as ctx:
            llm.complete_text("s", "u")
        self.assertEqual(ctx.exception.code, "llm_not_configured")

    @override_settings(LLM_FALLBACK_CHAIN="groq:b")
    def test_attachments_with_no_multimodal_provider_says_so(self):
        with self.assertRaises(ServiceError) as ctx:
            llm.complete_text("s", "u", attachments=[{"mime_type": "image/png", "data": "x"}])
        self.assertIn("Gemini", ctx.exception.detail)

    @override_settings(LLM_FALLBACK_CHAIN="gemini:a,gemini:b")
    def test_json_parsing_still_works_through_the_chain(self):
        with patch.dict(llm.PROVIDERS, {"gemini": lambda m, *a: '{"ok": true}'}):
            self.assertEqual(llm.complete_json("s", "u"), {"ok": True})

import unittest
from unittest.mock import Mock, patch

import requests

import ai_fallback


def _http_response(status_code, payload=None):
    response = Mock(status_code=status_code)
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(
            response=response
        )
    else:
        response.json.return_value = payload
    return response


class GeminiFallbackTests(unittest.TestCase):
    def setUp(self):
        self.previous_model = ai_fallback._last_good_model
        ai_fallback._last_good_model = None

    def tearDown(self):
        ai_fallback._last_good_model = self.previous_model

    def test_skips_missing_and_empty_models_then_tries_next_after_busy(self):
        responses = [
            _http_response(404),
            _http_response(503),
            _http_response(
                200,
                {"candidates": [{"content": {"parts": [{"text": "success"}]}}]},
            ),
        ]
        with patch.object(
            ai_fallback,
            "_gemini_candidates",
            return_value=["missing-model", "", "busy-model", "working-model"],
        ), patch.object(ai_fallback.requests, "post", side_effect=responses) as post:
            result = ai_fallback._call_gemini("hello", "", "test-key")

        self.assertEqual(result, "success")
        requested_models = [call.args[0].split("/")[-1].split(":")[0] for call in post.call_args_list]
        self.assertEqual(
            requested_models,
            ["missing-model", "busy-model", "working-model"],
        )

    def test_model_discovery_failure_uses_only_nonempty_preferences(self):
        with patch.object(
            ai_fallback,
            "GEMINI_PREFERRED",
            ["", "first-model", "second-model"],
        ), patch.object(
            ai_fallback.requests, "get", side_effect=requests.Timeout("offline")
        ):
            self.assertEqual(
                ai_fallback._gemini_candidates("test-key"),
                ["first-model", "second-model"],
            )

    def test_model_discovery_excludes_unconfigured_flash_models(self):
        response = Mock()
        response.json.return_value = {
            "models": [
                {
                    "name": "models/gemini-3.6-flash",
                    "supportedGenerationMethods": ["generateContent"],
                },
                {
                    "name": "models/gemini-9-flash",
                    "supportedGenerationMethods": ["generateContent"],
                },
            ]
        }
        with patch.object(ai_fallback.requests, "get", return_value=response):
            self.assertEqual(
                ai_fallback._gemini_candidates("test-key"),
                ["gemini-3.6-flash"],
            )

    def test_ask_gemini_uses_shared_candidate_fallback(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), patch.object(
            ai_fallback, "_call_gemini", return_value="success"
        ) as call:
            self.assertEqual(ai_fallback.ask_gemini("hello"), "success")

        call.assert_called_once_with("hello", ai_fallback.GEMINI_BASE, "test-key")


if __name__ == "__main__":
    unittest.main()

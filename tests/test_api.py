"""Tests for utils.api — HTTP / auth helpers."""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import MagicMock, patch
import urllib.error

from utils.api import (
    AnthropicProvider,
    OpenAIProvider,
    fetch_models,
    get_models_endpoint,
    get_provider,
    normalize_endpoint,
    test_endpoint_connectivity,
)


class TestEndpointHelpers(unittest.TestCase):
    def test_normalize_endpoint_empty(self):
        self.assertEqual(normalize_endpoint(""), "")
        self.assertEqual(normalize_endpoint("   "), "")

    def test_normalize_endpoint_base_url(self):
        self.assertEqual(normalize_endpoint("http://192.168.1.6:1234"), "http://192.168.1.6:1234/v1/chat/completions")
        self.assertEqual(normalize_endpoint("http://localhost:11434"), "http://localhost:11434/v1/chat/completions")
        self.assertEqual(normalize_endpoint("https://api.openai.com"), "https://api.openai.com/v1/chat/completions")

    def test_normalize_endpoint_with_v1(self):
        self.assertEqual(normalize_endpoint("http://localhost:1234/v1"), "http://localhost:1234/v1/chat/completions")
        self.assertEqual(normalize_endpoint("http://localhost:1234/v1/"), "http://localhost:1234/v1/chat/completions")

    def test_normalize_endpoint_already_complete(self):
        url = "http://192.168.1.6:1234/v1/chat/completions"
        self.assertEqual(normalize_endpoint(url), url)
        ollama_url = "http://localhost:11434/api/chat"
        self.assertEqual(normalize_endpoint(ollama_url), ollama_url)

    def test_normalize_endpoint_anthropic(self):
        self.assertEqual(normalize_endpoint("https://api.anthropic.com"), "https://api.anthropic.com/v1/messages")
        self.assertEqual(normalize_endpoint("https://api.anthropic.com/v1"), "https://api.anthropic.com/v1/messages")
        self.assertEqual(normalize_endpoint("https://api.anthropic.com/v1/messages"), "https://api.anthropic.com/v1/messages")

    def test_get_models_endpoint(self):
        self.assertEqual(get_models_endpoint("http://localhost:1234"), "http://localhost:1234/v1/models")
        self.assertEqual(get_models_endpoint("http://localhost:1234/v1/chat/completions"), "http://localhost:1234/v1/models")
        self.assertEqual(get_models_endpoint("http://localhost:11434/api/chat"), "http://localhost:11434/api/tags")


class TestFetchModels(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_fetch_models_openai_format(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"data": [{"id": "qwen2.5-coder-3b-instruct"}, {"id": "llama-3-8b"}]}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        models = fetch_models("http://localhost:1234")
        self.assertEqual(models, ["qwen2.5-coder-3b-instruct", "llama-3-8b"])

    @patch("urllib.request.urlopen")
    def test_fetch_models_ollama_format(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"models": [{"name": "qwen2.5-coder:3b"}, {"name": "deepseek-coder:6.7b"}]}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        models = fetch_models("http://localhost:11434/api/chat")
        self.assertEqual(models, ["qwen2.5-coder:3b", "deepseek-coder:6.7b"])

    @patch("urllib.request.urlopen")
    def test_fetch_models_error_returns_empty(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        models = fetch_models("http://localhost:9999")
        self.assertEqual(models, [])


class TestConnectivity(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_connectivity_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        is_ok, msg = test_endpoint_connectivity("http://localhost:1234")
        self.assertTrue(is_ok)

    @patch("urllib.request.urlopen")
    def test_connectivity_http_401_still_reachable(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)

        is_ok, msg = test_endpoint_connectivity("https://api.openai.com")
        self.assertTrue(is_ok)
        self.assertIn("401", msg)

    @patch("urllib.request.urlopen")
    def test_connectivity_connection_refused(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused [Errno 111]")

        is_ok, msg = test_endpoint_connectivity("http://127.0.0.1:9999")
        self.assertFalse(is_ok)
        self.assertIn("Connection refused", msg)


class TestGetProvider(unittest.TestCase):
    def test_get_provider_by_endpoint(self):
        self.assertIsInstance(get_provider("https://api.openai.com/v1/chat/completions"), OpenAIProvider)
        self.assertIsInstance(get_provider("http://localhost:11434/v1/chat/completions"), OpenAIProvider)
        self.assertIsInstance(get_provider("https://api.anthropic.com/v1/messages"), AnthropicProvider)
        self.assertIsInstance(get_provider("https://my-proxy.com/v1/messages"), AnthropicProvider)

    def test_get_provider_by_setting(self):
        self.assertIsInstance(get_provider("https://api.example.com", {"provider": "anthropic"}), AnthropicProvider)
        self.assertIsInstance(get_provider("https://api.anthropic.com/v1/messages", {"provider": "openai"}), OpenAIProvider)


class TestOpenAIProvider(unittest.TestCase):
    def setUp(self):
        self.provider = OpenAIProvider()

    def test_build_headers_with_key(self):
        settings = {"api_key": "sk-abc123"}
        headers = self.provider.build_headers(settings)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Authorization"], "Bearer sk-abc123")

    def test_build_headers_without_key(self):
        settings = {"api_key": ""}
        headers = self.provider.build_headers(settings)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertNotIn("Authorization", headers)

    def test_format_payload(self):
        messages = [{"role": "user", "content": "hi"}]
        payload = self.provider.format_payload("gpt-4", messages, 100, 0.5)
        self.assertEqual(payload["model"], "gpt-4")
        self.assertEqual(payload["messages"], messages)
        self.assertEqual(payload["max_tokens"], 100)
        self.assertEqual(payload["temperature"], 0.5)
        self.assertNotIn("stream", payload)

    def test_parse_response(self):
        result = {"choices": [{"message": {"content": " hello  "}}]}
        self.assertEqual(self.provider.parse_response(result), "hello")


class TestAnthropicProvider(unittest.TestCase):
    def setUp(self):
        self.provider = AnthropicProvider()

    def test_build_headers_with_key(self):
        settings = {"api_key": "sk-ant123"}
        headers = self.provider.build_headers(settings)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["x-api-key"], "sk-ant123")
        self.assertEqual(headers["anthropic-version"], "2023-06-01")

    def test_format_payload(self):
        messages = [
            {"role": "system", "content": "You are a bot"},
            {"role": "user", "content": "hi"}
        ]
        payload = self.provider.format_payload("claude-3", messages, 100, 0.5)
        self.assertEqual(payload["model"], "claude-3")
        self.assertEqual(payload["max_tokens"], 100)
        self.assertEqual(payload["temperature"], 0.5)
        self.assertEqual(payload["system"], "You are a bot")
        self.assertEqual(len(payload["messages"]), 1)
        self.assertEqual(payload["messages"][0]["role"], "user")

    def test_parse_response(self):
        result = {"content": [{"text": " hello  "}]}
        self.assertEqual(self.provider.parse_response(result), "hello")


if __name__ == "__main__":
    unittest.main()


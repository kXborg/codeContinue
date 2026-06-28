"""Tests for utils.api — HTTP / auth helpers."""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.api import OpenAIProvider, AnthropicProvider, get_provider


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

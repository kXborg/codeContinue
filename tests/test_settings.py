"""Tests for utils.settings — is_endpoint_configured helper.

The settings module imports `sublime` and `sublime_plugin` at the top level,
which are only available inside the Sublime Text runtime.  We inject minimal
stubs so the import succeeds in a plain-Python test environment.
"""

import sys
import os
import types
import unittest

# --- Stub out Sublime modules before importing the code under test ----------
_sublime_stub = types.ModuleType("sublime")
_sublime_plugin_stub = types.ModuleType("sublime_plugin")

# Provide the TextCommand base class that CodeContinueConfigureCommand inherits.
class _StubTextCommand:
    pass

_sublime_plugin_stub.TextCommand = _StubTextCommand

sys.modules.setdefault("sublime", _sublime_stub)
sys.modules.setdefault("sublime_plugin", _sublime_plugin_stub)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.settings import is_endpoint_configured


class _FakeSettings(dict):
    """Minimal dict-like that also exposes .get(), matching Sublime's Settings API."""
    pass  # dict already has .get()


class TestIsEndpointConfigured(unittest.TestCase):
    """is_endpoint_configured should detect real vs placeholder endpoints."""

    def test_valid_openai_endpoint(self):
        s = _FakeSettings(endpoint="https://api.openai.com/v1/chat/completions")
        self.assertTrue(is_endpoint_configured(s))

    def test_valid_local_endpoint(self):
        s = _FakeSettings(endpoint="http://localhost:8000/v1/chat/completions")
        self.assertTrue(is_endpoint_configured(s))

    def test_placeholder_endpoint(self):
        s = _FakeSettings(endpoint="https://your-api.com/v1/chat/completions")
        self.assertFalse(is_endpoint_configured(s))

    def test_placeholder_case_insensitive(self):
        s = _FakeSettings(endpoint="https://YOUR-API.example.com/v1")
        self.assertFalse(is_endpoint_configured(s))

    def test_empty_endpoint(self):
        s = _FakeSettings(endpoint="")
        self.assertFalse(is_endpoint_configured(s))

    def test_missing_endpoint(self):
        s = _FakeSettings()
        self.assertFalse(is_endpoint_configured(s))

    def test_whitespace_only_endpoint(self):
        s = _FakeSettings(endpoint="   ")
        self.assertFalse(is_endpoint_configured(s))

    def test_huggingface_endpoint(self):
        s = _FakeSettings(endpoint="https://api-inference.huggingface.co/v1/chat/completions")
        self.assertTrue(is_endpoint_configured(s))

    def test_endpoint_with_your_api_substring(self):
        """Any URL containing 'your-api' is treated as a placeholder."""
        s = _FakeSettings(endpoint="http://my-your-api-server.local/v1")
        self.assertFalse(is_endpoint_configured(s))


if __name__ == "__main__":
    unittest.main()

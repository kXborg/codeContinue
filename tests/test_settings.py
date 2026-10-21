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

# Provide base classes that CodeContinue commands inherit.
class _StubCommand:
    pass

_sublime_plugin_stub.TextCommand = _StubCommand
_sublime_plugin_stub.ApplicationCommand = _StubCommand
_sublime_plugin_stub.WindowCommand = _StubCommand

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

    def test_endpoint_with_trycloudflare(self):
        """Any URL containing 'trycloudflare.com' is treated as a placeholder/expired tunnel."""
        s = _FakeSettings(endpoint="https://ryan-float-cookie-emissions.trycloudflare.com/v1/chat/completions")
        self.assertFalse(is_endpoint_configured(s))


from utils.settings import (
    DEFAULT_ENDPOINT,
    FeatureSettings,
    get_default_or_configured_endpoint,
    get_feature_settings,
)


class TestGetDefaultOrConfiguredEndpoint(unittest.TestCase):
    def test_empty_returns_default(self):
        self.assertEqual(get_default_or_configured_endpoint(_FakeSettings(endpoint="")), DEFAULT_ENDPOINT)
        self.assertEqual(get_default_or_configured_endpoint(_FakeSettings()), DEFAULT_ENDPOINT)
        self.assertEqual(get_default_or_configured_endpoint(None), DEFAULT_ENDPOINT)

    def test_cloudflare_tunnel_returns_default(self):
        s = _FakeSettings(endpoint="https://ryan-float-cookie-emissions.trycloudflare.com/v1/chat/completions")
        self.assertEqual(get_default_or_configured_endpoint(s), DEFAULT_ENDPOINT)

    def test_your_api_placeholder_returns_default(self):
        s = _FakeSettings(endpoint="https://your-api.com/v1/chat/completions")
        self.assertEqual(get_default_or_configured_endpoint(s), DEFAULT_ENDPOINT)

    def test_configured_endpoint_preserved(self):
        s = _FakeSettings(endpoint="https://api.openai.com/v1/chat/completions")
        self.assertEqual(get_default_or_configured_endpoint(s), "https://api.openai.com/v1/chat/completions")


class TestFeatureSettings(unittest.TestCase):
    def test_global_fallback_when_no_override(self):
        raw = _FakeSettings(
            endpoint="http://localhost:8000/v1/chat/completions",
            model="qwen2.5-coder:1.5b",
            api_key="",
            timeout_ms=30000,
        )
        chat_cfg = get_feature_settings(raw, "chat")
        self.assertEqual(chat_cfg.get("endpoint"), "http://localhost:8000/v1/chat/completions")
        self.assertEqual(chat_cfg.get("model"), "qwen2.5-coder:1.5b")
        self.assertEqual(chat_cfg.get("timeout_ms"), 30000)

    def test_feature_override_takes_precedence(self):
        raw = _FakeSettings(
            endpoint="http://localhost:8000/v1/chat/completions",
            model="qwen2.5-coder:1.5b",
            api_key="",
            chat_endpoint="https://api.anthropic.com/v1/messages",
            chat_model="claude-3-5-sonnet-20241022",
            chat_api_key="sk-ant-test",
            edit_model="gpt-4o",
        )
        chat_cfg = get_feature_settings(raw, "chat")
        self.assertEqual(chat_cfg.get("endpoint"), "https://api.anthropic.com/v1/messages")
        self.assertEqual(chat_cfg.get("model"), "claude-3-5-sonnet-20241022")
        self.assertEqual(chat_cfg.get("api_key"), "sk-ant-test")

        edit_cfg = get_feature_settings(raw, "edit")
        self.assertEqual(edit_cfg.get("model"), "gpt-4o")
        self.assertEqual(edit_cfg.get("endpoint"), "http://localhost:8000/v1/chat/completions")

        completion_cfg = get_feature_settings(raw, "completion")
        self.assertEqual(completion_cfg.get("model"), "qwen2.5-coder:1.5b")

    def test_empty_string_override_falls_back_to_global(self):
        raw = _FakeSettings(
            endpoint="http://localhost:8000/v1/chat/completions",
            model="qwen2.5-coder:1.5b",
            chat_model="",
        )
        chat_cfg = get_feature_settings(raw, "chat")
        self.assertEqual(chat_cfg.get("model"), "qwen2.5-coder:1.5b")

    def test_none_settings_handled(self):
        cfg = get_feature_settings(None, "chat")
        self.assertIsNone(cfg.get("model"))
        self.assertEqual(cfg.get("model", "default_val"), "default_val")


from utils.settings import update_status_bar


class _FakeView:
    def __init__(self, scratch=False):
        self.status = {}
        self._scratch = scratch

    def is_valid(self):
        return True

    def is_scratch(self):
        return self._scratch

    def set_status(self, key, value):
        self.status[key] = value

    def erase_status(self, key):
        self.status.pop(key, None)


class TestUpdateStatusBar(unittest.TestCase):
    def setUp(self):
        self.fake_settings = _FakeSettings(model="qwen2.5-coder", status_bar=True)
        # Ensure sublime.load_settings returns our fake settings
        _sublime_stub.load_settings = lambda name: self.fake_settings

    def test_normal_model_display(self):
        view = _FakeView()
        update_status_bar(view)
        self.assertEqual(view.status.get("code_continue_status"), "CodeContinue: [qwen2.5-coder]")

    def test_state_text_display(self):
        view = _FakeView()
        update_status_bar(view, "Suggesting...")
        self.assertEqual(view.status.get("code_continue_status"), "CodeContinue: [qwen2.5-coder] Suggesting...")

    def test_scratch_view_ignored(self):
        view = _FakeView(scratch=True)
        update_status_bar(view)
        self.assertNotIn("code_continue_status", view.status)

    def test_disabled_status_bar_erases(self):
        self.fake_settings["status_bar"] = False
        view = _FakeView()
        view.status["code_continue_status"] = "old_status"
        update_status_bar(view)
        self.assertNotIn("code_continue_status", view.status)


from utils.settings import (
    get_keybinding_preset,
    get_user_keymap_path,
    install_user_keybindings,
)
import tempfile
import json
import shutil


class TestKeybindingPresets(unittest.TestCase):
    def test_recommended_preset(self):
        preset = get_keybinding_preset("recommended")
        self.assertEqual(len(preset), 3)
        commands = [b["command"] for b in preset]
        self.assertIn("code_continue_accept", commands)
        self.assertIn("code_continue_suggest", commands)
        self.assertIn("code_continue_dismiss", commands)

        # Tab accept must have code_continue_visible context
        tab_binding = next(b for b in preset if b["keys"] == ["tab"])
        self.assertEqual(tab_binding["command"], "code_continue_accept")
        self.assertTrue(any(c.get("key") == "code_continue_visible" for c in tab_binding["context"]))

    def test_single_key_preset(self):
        preset = get_keybinding_preset("single_key")
        self.assertEqual(len(preset), 3)
        ctrl_enter_bindings = [b for b in preset if b["keys"] == ["ctrl+enter"]]
        self.assertEqual(len(ctrl_enter_bindings), 2)
        # First has context, second is fallback suggest
        self.assertEqual(ctrl_enter_bindings[0]["command"], "code_continue_accept")
        self.assertEqual(ctrl_enter_bindings[1]["command"], "code_continue_suggest")


class TestInstallUserKeybindings(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_creates_new_keymap_file(self):
        ok, msg = install_user_keybindings(preset="recommended", packages_path=self.tmp_dir)
        self.assertTrue(ok)
        keymap_file = get_user_keymap_path(self.tmp_dir)
        self.assertTrue(os.path.exists(keymap_file))

        with open(keymap_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 3)

    def test_merges_and_cleans_old_bindings(self):
        user_dir = os.path.join(self.tmp_dir, "User")
        os.makedirs(user_dir, exist_ok=True)
        keymap_file = get_user_keymap_path(self.tmp_dir)

        initial = [
            {"keys": ["ctrl+shift+x"], "command": "custom_user_command"},
            {"keys": ["tab"], "command": "code_continue_accept"},
            {"keys": ["alt+/"], "command": "code_continue_suggest"},
        ]
        with open(keymap_file, "w", encoding="utf-8") as f:
            json.dump(initial, f)

        ok, msg = install_user_keybindings(preset="recommended", packages_path=self.tmp_dir)
        self.assertTrue(ok)

        with open(keymap_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # custom_user_command must be preserved
        self.assertTrue(any(b.get("command") == "custom_user_command" for b in data))
        # Old alt+/ suggestion must be replaced
        self.assertFalse(any(b.get("keys") == ["alt+/"] for b in data))
        # Total: 1 custom + 3 recommended = 4
        self.assertEqual(len(data), 4)


if __name__ == "__main__":
    unittest.main()


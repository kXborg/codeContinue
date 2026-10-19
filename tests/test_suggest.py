"""Tests for utils.suggest — is_syntax_supported helper."""

import os
import sys
import types
import unittest

# --- Ensure sublime and sublime_plugin stubs exist in sys.modules ------------
if "sublime" not in sys.modules:
    sys.modules["sublime"] = types.ModuleType("sublime")
if "sublime_plugin" not in sys.modules:
    sys.modules["sublime_plugin"] = types.ModuleType("sublime_plugin")

sublime_mod = sys.modules["sublime"]
sublime_plugin_mod = sys.modules["sublime_plugin"]


class _StubEventListener:
    pass


class _StubTextCommand:
    pass


if not hasattr(sublime_plugin_mod, "EventListener"):
    setattr(sublime_plugin_mod, "EventListener", _StubEventListener)
if not hasattr(sublime_plugin_mod, "TextCommand"):
    setattr(sublime_plugin_mod, "TextCommand", _StubTextCommand)
if not hasattr(sublime_mod, "load_settings"):
    setattr(sublime_mod, "load_settings", lambda x: {})
if not hasattr(sublime_mod, "status_message"):
    setattr(sublime_mod, "status_message", lambda x: None)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.suggest import is_syntax_supported


class FakeSyntax:

    def __init__(self, name="", scope=""):
        self.name = name
        self.scope = scope


class TestIsSyntaxSupported(unittest.TestCase):

    def test_exact_name_match(self):
        syntax = FakeSyntax(name="Python", scope="source.python")
        self.assertTrue(is_syntax_supported(syntax, ["python", "cpp"]))

    def test_cpp_alias(self):
        syntax = FakeSyntax(name="C++", scope="source.c++")
        self.assertTrue(is_syntax_supported(syntax, ["cpp", "python"]))

    def test_javascript_alias(self):
        syntax = FakeSyntax(name="JavaScript (Babel)", scope="source.js")
        self.assertTrue(is_syntax_supported(syntax, ["javascript"]))
        self.assertTrue(is_syntax_supported(syntax, ["js"]))

    def test_wildcard_matching(self):
        syntax = FakeSyntax(name="Plain Text", scope="text.plain")
        self.assertTrue(is_syntax_supported(syntax, ["*"]))
        self.assertTrue(is_syntax_supported(syntax, ["all"]))

    def test_unmatched_syntax(self):
        syntax = FakeSyntax(name="Plain Text", scope="text.plain")
        self.assertFalse(is_syntax_supported(syntax, ["python", "cpp"]))

    def test_none_syntax(self):
        self.assertFalse(is_syntax_supported(None, ["python"]))

    def test_empty_trigger_langs(self):
        syntax = FakeSyntax(name="Python")
        self.assertFalse(is_syntax_supported(syntax, []))


class FakeView:
    def __init__(self, vid=1):
        self._id = vid

    def id(self):
        return self._id


from utils.suggest import (
    CodeContinueListener,
    CodeContinueAcceptCommand,
    CodeContinueDismissCommand,
    SuggestState,
    _states,
)


class TestQueryContextAndAccept(unittest.TestCase):
    def setUp(self):
        _states.clear()
        self.listener = CodeContinueListener()
        self.view = FakeView(vid=42)

    def tearDown(self):
        _states.clear()

    def test_query_context_unhandled_key(self):
        self.assertIsNone(self.listener.on_query_context(self.view, "some_other_key", 0, True, False))

    def test_query_context_no_suggestion_visible(self):
        # No phantom state exists
        self.assertFalse(self.listener.on_query_context(self.view, "code_continue_visible", 0, True, False))

    def test_query_context_suggestion_visible(self):
        st = SuggestState()
        st.phantom_set = object()  # dummy truthy
        st.remaining_lines = ["print('hello')"]
        _states[42] = st

        self.assertTrue(self.listener.on_query_context(self.view, "code_continue_visible", 0, True, False))
        self.assertFalse(self.listener.on_query_context(self.view, "code_continue_visible", 1, True, False))

    def test_accept_command_is_enabled(self):
        cmd = CodeContinueAcceptCommand()
        cmd.view = self.view

        self.assertFalse(cmd.is_enabled())

        st = SuggestState()
        st.phantom_set = object()
        st.remaining_lines = ["line1"]
        _states[42] = st

        self.assertTrue(cmd.is_enabled())
        self.assertTrue(cmd.is_visible())

    def test_dismiss_command_is_enabled(self):
        cmd = CodeContinueDismissCommand()
        cmd.view = self.view

        self.assertFalse(cmd.is_enabled())

        st = SuggestState()
        st.phantom_set = object()
        _states[42] = st

        self.assertTrue(cmd.is_enabled())
        self.assertTrue(cmd.is_visible())

    def test_on_text_command_ignored_when_auto_suggest_false(self):
        # auto_suggest_on_enter is false by default in load_settings stub
        res = self.listener.on_text_command(self.view, "insert", {"characters": "\n"})
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()


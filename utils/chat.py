"""Chat-about-selection feature: opens a split-pane Markdown chat view."""

import json
import threading
import urllib.error
import urllib.request

import sublime
import sublime_plugin

from .api import get_provider
from .log import _log
from .text_utils import describe_code_selection


class ChatState:
    """Per-chat-view state for the chat-about-selection feature.

    Replaces the former module-level dicts/sets (``_chat_sessions``,
    ``_chat_view_ids``, ``_original_layouts``, ``_chat_requesting``).
    Accessed via the module-level ``_states`` dict, keyed on ``chat_view.id()``.
    """

    __slots__ = (
        "history",
        "endpoint",
        "model",
        "timeout_s",
        "headers",
        "code",
        "lang",
        "file_name",
        "requesting",
        "provider",
    )

    def __init__(self, history, endpoint, model, timeout_s, headers, code, lang, file_name, provider):
        self.history = history
        self.endpoint = endpoint
        self.model = model
        self.timeout_s = timeout_s
        self.headers = headers
        self.code = code
        self.lang = lang
        self.file_name = file_name
        self.requesting = False  # True while an API call is in-flight
        self.provider = provider


# chat_view.id() -> ChatState
_states = {}
# window.id() -> original layout, restored when the chat view closes
_original_layouts = {}


CHAT_SYSTEM_PROMPT = (
    "You are a code discussion assistant running in a read-only chat panel in Sublime Text. "
    "The user has selected a piece of code and wants to discuss it.\n\n"
    "Guidelines:\n"
    "- Provide clear, concise explanations and practical suggestions.\n"
    "- You cannot directly modify files, buffers, or the user's selection from this chat window.\n"
    "- If the user asks whether you can edit code, or asks you to edit/rewrite/modify the code:\n"
    "  1. Clearly state that this chat panel is read-only and cannot edit their buffer directly.\n"
    "  2. Proactively explain how to edit in-place: 'Select your code >> right-click >> choose **CodeContinue: Edit Selection** (or press Ctrl+Shift+P >> CodeContinue: Edit Selection) and enter your instruction in the input field at the bottom.'\n"
    "  3. If they asked for a specific code change, provide the complete rewritten code in a markdown code block so they can copy/paste it.\n"
    "  4. Do NOT ask them to provide the code again; the selected code is already in the context.\n"
    "- Never claim that you applied changes or modified their files.\n"
    "- When showing code, use markdown formatting with language tags.\n"
    "- Be direct, practical, and concise."
)

INPUT_SEPARATOR = "\n---\n\n### 👤 You *(press Enter to send)*\n\n> "


def _chat_view_append(chat_view, text):
    """Append text to a chat view, preserving its read-only state."""
    was_read_only = chat_view.is_read_only()
    chat_view.set_read_only(False)
    chat_view.run_command("append", {"characters": text})
    if was_read_only:
        chat_view.set_read_only(True)
    chat_view.run_command("move_to", {"to": "eof"})


def _chat_get_user_input(chat_view):
    """Extract the user's typed text (everything after the last separator)."""
    content = chat_view.substr(sublime.Region(0, chat_view.size()))
    sep_pos = content.rfind(INPUT_SEPARATOR)
    if sep_pos == -1:
        return ""
    input_start = sep_pos + len(INPUT_SEPARATOR)
    text = content[input_start:].strip()
    if text.startswith(">"):
        text = text[1:].strip()
    return text


def _chat_show_input_area(chat_view):
    """Append the input separator and unlock for typing."""
    chat_view.set_read_only(False)
    chat_view.run_command("append", {"characters": INPUT_SEPARATOR})
    chat_view.run_command("move_to", {"to": "eof"})


def _chat_lock_and_format_input(chat_view, user_text):
    """Replace the input area with a formatted user message and lock the view."""
    content = chat_view.substr(sublime.Region(0, chat_view.size()))
    sep_pos = content.rfind(INPUT_SEPARATOR)
    if sep_pos < 0:
        return

    before = content[:sep_pos]
    chat_view.set_read_only(False)
    chat_view.run_command("select_all")
    chat_view.run_command("left_delete")
    chat_view.run_command("append", {"characters": before + "\n\n---\n\n### 👤 You\n\n" + user_text + "\n"})
    chat_view.set_read_only(True)


def _chat_remove_thinking(chat_view):
    """Remove the Thinking indicator from the chat view."""
    content = chat_view.substr(sublime.Region(0, chat_view.size()))
    marker = "\n---\n\n⏳ *Thinking...*\n"
    pos = content.rfind(marker)
    if pos >= 0:
        cleaned = content[:pos] + content[pos + len(marker):]
        chat_view.set_read_only(False)
        chat_view.run_command("select_all")
        chat_view.run_command("left_delete")
        chat_view.run_command("append", {"characters": cleaned})
        chat_view.set_read_only(True)
    else:
        marker_short = "\n⏳ *Thinking...*\n"
        pos = content.rfind(marker_short)
        if pos >= 0:
            cleaned = content[:pos] + content[pos + len(marker_short):]
            chat_view.set_read_only(False)
            chat_view.run_command("select_all")
            chat_view.run_command("left_delete")
            chat_view.run_command("append", {"characters": cleaned})
            chat_view.set_read_only(True)


def _chat_do_api_call(chat_view, state):
    """Send conversation history to LLM and render the response in the chat view."""
    cvid = chat_view.id()

    if not state.endpoint or not state.model:
        sublime.set_timeout(lambda: _chat_view_append(chat_view, "\n⚠ Error: endpoint or model not configured.\n"), 0)
        state.requesting = False
        return

    data = state.provider.format_payload(state.model, state.history, 2048, 0.5)

    _log("Chat: Sending request to {0}".format(state.endpoint))

    def do_request():
        try:
            req = urllib.request.Request(
                state.endpoint,
                data=json.dumps(data).encode(),
                headers=state.headers,
            )
            with urllib.request.urlopen(req, timeout=state.timeout_s) as response:
                result = json.loads(response.read().decode())
                reply = state.provider.parse_response(result)

                if reply:
                    state.history.append({"role": "assistant", "content": reply})

                    def show_reply():
                        if cvid not in _states:
                            return
                        _chat_remove_thinking(chat_view)
                        _chat_view_append(chat_view, "\n---\n\n### 🤖 CodeContinue\n\n" + reply + "\n")
                        _chat_show_input_area(chat_view)
                        state.requesting = False

                    sublime.set_timeout(show_reply, 0)
                else:
                    def show_empty():
                        if cvid not in _states:
                            return
                        _chat_remove_thinking(chat_view)
                        _chat_view_append(chat_view, "\n⚠ Empty response from model.\n")
                        _chat_show_input_area(chat_view)
                        state.requesting = False
                    sublime.set_timeout(show_empty, 0)

        except urllib.error.URLError as e:
            _log("Chat: Network error: {0}".format(str(e)[:100]))
            def show_net_err():
                if cvid not in _states:
                    return
                _chat_remove_thinking(chat_view)
                _chat_view_append(chat_view, "\n⚠ Network error: {0}\n".format(str(e)[:100]))
                _chat_show_input_area(chat_view)
                state.requesting = False
            sublime.set_timeout(show_net_err, 0)
        except Exception as e:
            _log("Chat: Error: {0}".format(str(e)[:100]))
            def show_gen_err():
                if cvid not in _states:
                    return
                _chat_remove_thinking(chat_view)
                _chat_view_append(chat_view, "\n⚠ Error: {0}\n".format(str(e)[:100]))
                _chat_show_input_area(chat_view)
                state.requesting = False
            sublime.set_timeout(show_gen_err, 0)

    thread = threading.Thread(target=do_request)
    thread.daemon = True
    thread.start()


def _chat_send_message(chat_view):
    """Extract user input, format it, and send to LLM."""
    cvid = chat_view.id()
    state = _states.get(cvid)
    if not state or state.requesting:
        return

    user_text = _chat_get_user_input(chat_view)
    if not user_text:
        return

    state.requesting = True
    _chat_lock_and_format_input(chat_view, user_text)

    # First user message includes selected code context
    if len(state.history) <= 1:
        content = (
            "Here is the selected code from `{0}` ({1}):\n\n"
            "```{1}\n{2}\n```\n\n"
            "{3}"
        ).format(state.file_name, state.lang, state.code, user_text)
    else:
        content = user_text

    state.history.append({"role": "user", "content": content})
    _chat_view_append(chat_view, "\n---\n\n⏳ *Thinking...*\n")
    _chat_do_api_call(chat_view, state)


class ChatEventListener(sublime_plugin.EventListener):
    """Handle Enter key and view close in chat views."""

    def on_text_command(self, view, command_name, args):
        if view.id() not in _states:
            return None

        if command_name == "insert" and args and args.get("characters") == "\n":
            state = _states.get(view.id())
            user_text = _chat_get_user_input(view)
            if user_text and state and not state.requesting:
                _chat_send_message(view)
                return ("noop", None)

        return None

    def on_close(self, view):
        """Clean up when a chat view is closed and restore window layout."""
        vid = view.id()
        if vid not in _states:
            return

        _states.pop(vid, None)

        window = sublime.active_window()
        if window and window.id() in _original_layouts:
            layout = _original_layouts.pop(window.id())
            sublime.set_timeout(lambda: window.set_layout(layout), 100)
            _log("Chat: Restored original layout")


class CodeContinueChatCommand(sublime_plugin.TextCommand):
    """Open a split-window chat about selected code."""

    def run(self, edit):
        view = self.view
        window = view.window()
        if not window:
            return

        settings = sublime.load_settings("CodeContinue.sublime-settings")

        selected_text = ""
        for region in view.sel():
            if not region.empty():
                selected_text += view.substr(region) + "\n"

        selected_text = selected_text.strip()
        if not selected_text:
            sublime.status_message("CodeContinue: No text selected")
            return

        file_name = view.file_name() or "untitled"
        syntax = view.settings().get("syntax", "")
        lang = syntax.split("/")[-1].replace(".sublime-syntax", "").lower() if syntax else "unknown"
        base_name = file_name.split("\\")[-1].split("/")[-1]

        wid = window.id()
        _original_layouts[wid] = window.get_layout()

        window.set_layout({
            "cols": [0.0, 0.6, 1.0],
            "rows": [0.0, 1.0],
            "cells": [[0, 0, 1, 1], [1, 0, 2, 1]],
        })

        window.set_view_index(view, 0, 0)

        chat_view = window.new_file()
        chat_view.set_name("Chat - " + base_name)
        chat_view.set_scratch(True)
        chat_view.assign_syntax("Packages/Markdown/Markdown.sublime-syntax")
        chat_view.settings().set("word_wrap", True)
        chat_view.settings().set("gutter", False)
        chat_view.settings().set("line_numbers", False)
        chat_view.settings().set("rulers", [])
        chat_view.settings().set("draw_indent_guides", False)
        window.set_view_index(chat_view, 1, 0)
        window.focus_view(chat_view)

        cvid = chat_view.id()

        endpoint = settings.get("endpoint", "")
        provider = get_provider(endpoint, settings)
        
        state = ChatState(
            history=[
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            ],
            endpoint=endpoint,
            model=settings.get("model", ""),
            timeout_s=settings.get("timeout_ms", 30000) / 1000.0,
            headers=provider.build_headers(settings),
            code=selected_text,
            lang=lang,
            file_name=base_name,
            provider=provider,
        )
        _states[cvid] = state

        description = describe_code_selection(selected_text, lang)
        greeting = "Hi, I see you have selected {0}; how can I help?".format(description)

        header = (
            "## CodeContinue Chat\n"
            "**File:** `{0}` | **Language:** `{1}`\n\n"
            "---\n\n"
            "### Selected Code\n"
            "```{1}\n"
            "{2}\n"
            "```\n\n"
            "---\n\n"
            "### 🤖 CodeContinue\n\n"
            "{3}\n"
        ).format(base_name, lang, selected_text, greeting)

        chat_view.run_command("append", {"characters": header})
        chat_view.set_read_only(True)
        _chat_show_input_area(chat_view)

    def is_enabled(self):
        """Only enable when there is a non-empty selection."""
        for region in self.view.sel():
            if not region.empty():
                return True
        return False


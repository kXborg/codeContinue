"""Chat-about-selection feature: opens a split-pane Markdown chat view."""

import json
import threading
import urllib.error
import urllib.request

import sublime
import sublime_plugin

from .api import build_api_headers
from .log import _log


# chat_view.id() -> session dict (history, endpoint, model, etc.)
_chat_sessions = {}
# chat_view.id() set: identifies chat views (used to gate event listeners)
_chat_view_ids = set()
# window.id() -> original layout, restored when the chat view closes
_original_layouts = {}
# chat_view.id() set: prevents re-entrant request sending
_chat_requesting = set()


CHAT_SYSTEM_PROMPT = (
    "You are a helpful code assistant. The user has selected a piece of code "
    "and wants to discuss it. Provide clear, concise explanations and suggestions. "
    "When showing code, use markdown formatting. Be direct and practical."
)

INPUT_SEPARATOR = "\n── Type below and press Enter to send (close tab to end) ──\n"


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
    return content[input_start:].strip()


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
    chat_view.run_command("append", {"characters": before + "\n\n You: " + user_text + "\n"})
    chat_view.set_read_only(True)


def _chat_remove_thinking(chat_view):
    """Remove the Thinking indicator from the chat view."""
    content = chat_view.substr(sublime.Region(0, chat_view.size()))
    marker = "\n⏳ Thinking...\n"
    pos = content.rfind(marker)
    if pos >= 0:
        cleaned = content[:pos] + content[pos + len(marker):]
        chat_view.set_read_only(False)
        chat_view.run_command("select_all")
        chat_view.run_command("left_delete")
        chat_view.run_command("append", {"characters": cleaned})
        chat_view.set_read_only(True)


def _chat_do_api_call(chat_view, session):
    """Send conversation history to LLM and render the response in the chat view."""
    cvid = chat_view.id()

    endpoint = session["endpoint"]
    model = session["model"]
    timeout_s = session["timeout_s"]
    headers = session["headers"]
    history = session["history"]

    if not endpoint or not model:
        sublime.set_timeout(lambda: _chat_view_append(chat_view, "\n⚠ Error: endpoint or model not configured.\n"), 0)
        _chat_requesting.discard(cvid)
        return

    data = {
        "model": model,
        "messages": history,
        "max_tokens": 2048,
        "temperature": 0.5,
    }

    _log("Chat: Sending request to {0}".format(endpoint))

    def do_request():
        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(data).encode(),
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=timeout_s) as response:
                result = json.loads(response.read().decode())
                reply = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

                if reply:
                    session["history"].append({"role": "assistant", "content": reply})

                    def show_reply():
                        if cvid not in _chat_view_ids:
                            return
                        _chat_remove_thinking(chat_view)
                        _chat_view_append(chat_view, "\n Assistant: " + reply + "\n")
                        _chat_show_input_area(chat_view)
                        _chat_requesting.discard(cvid)

                    sublime.set_timeout(show_reply, 0)
                else:
                    def show_empty():
                        if cvid not in _chat_view_ids:
                            return
                        _chat_remove_thinking(chat_view)
                        _chat_view_append(chat_view, "\n⚠ Empty response from model.\n")
                        _chat_show_input_area(chat_view)
                        _chat_requesting.discard(cvid)
                    sublime.set_timeout(show_empty, 0)

        except urllib.error.URLError as e:
            _log("Chat: Network error: {0}".format(str(e)[:100]))
            def show_net_err():
                if cvid not in _chat_view_ids:
                    return
                _chat_remove_thinking(chat_view)
                _chat_view_append(chat_view, "\n⚠ Network error: {0}\n".format(str(e)[:100]))
                _chat_show_input_area(chat_view)
                _chat_requesting.discard(cvid)
            sublime.set_timeout(show_net_err, 0)
        except Exception as e:
            _log("Chat: Error: {0}".format(str(e)[:100]))
            def show_gen_err():
                if cvid not in _chat_view_ids:
                    return
                _chat_remove_thinking(chat_view)
                _chat_view_append(chat_view, "\n⚠ Error: {0}\n".format(str(e)[:100]))
                _chat_show_input_area(chat_view)
                _chat_requesting.discard(cvid)
            sublime.set_timeout(show_gen_err, 0)

    thread = threading.Thread(target=do_request)
    thread.daemon = True
    thread.start()


def _chat_send_message(chat_view):
    """Extract user input, format it, and send to LLM."""
    cvid = chat_view.id()
    session = _chat_sessions.get(cvid)
    if not session or cvid in _chat_requesting:
        return

    user_text = _chat_get_user_input(chat_view)
    if not user_text:
        return

    _chat_requesting.add(cvid)
    _chat_lock_and_format_input(chat_view, user_text)
    session["history"].append({"role": "user", "content": user_text})
    _chat_view_append(chat_view, "\n⏳ Thinking...\n")
    _chat_do_api_call(chat_view, session)


class ChatEventListener(sublime_plugin.EventListener):
    """Handle Enter key and view close in chat views."""

    def on_text_command(self, view, command_name, args):
        if view.id() not in _chat_view_ids:
            return None

        if command_name == "insert" and args and args.get("characters") == "\n":
            user_text = _chat_get_user_input(view)
            if user_text and view.id() not in _chat_requesting:
                _chat_send_message(view)
                return ("noop", None)

        return None

    def on_close(self, view):
        """Clean up when a chat view is closed and restore window layout."""
        vid = view.id()
        if vid not in _chat_view_ids:
            return

        _chat_view_ids.discard(vid)
        _chat_sessions.pop(vid, None)
        _chat_requesting.discard(vid)

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
        _chat_view_ids.add(cvid)

        initial_msg = (
            "Here is the selected code from `{0}` ({1}):\n\n"
            "```\n{2}\n```\n\n"
            "I'd like to discuss this code."
        ).format(base_name, lang, selected_text)

        session = {
            "history": [
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {"role": "user", "content": initial_msg},
            ],
            "endpoint": settings.get("endpoint", ""),
            "model": settings.get("model", ""),
            "timeout_s": settings.get("timeout_ms", 30000) / 1000.0,
            "headers": build_api_headers(settings),
            "code": selected_text,
            "lang": lang,
        }
        _chat_sessions[cvid] = session

        header = (
            "═══ CodeContinue Chat ═══\n"
            "File: {0}  |  Language: {1}\n\n"
            "─── Selected Code ───\n"
            "{2}\n"
        ).format(base_name, lang, selected_text)

        chat_view.run_command("append", {"characters": header})
        chat_view.set_read_only(True)

        _chat_view_append(chat_view, "\n⏳ Thinking...\n")
        _chat_requesting.add(cvid)
        _chat_do_api_call(chat_view, session)

    def is_enabled(self):
        """Only enable when there is a non-empty selection."""
        for region in self.view.sel():
            if not region.empty():
                return True
        return False

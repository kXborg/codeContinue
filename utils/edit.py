"""Inline edit / refactor feature: Prompts for instruction and replaces selection."""

import json
import threading
import urllib.error
import urllib.request

import sublime
import sublime_plugin

from .api import build_api_headers
from .log import _log, _log_error
from .text_utils import clean_markdown_fences
from .settings import is_endpoint_configured, show_endpoint_config_panel


class CodeContinueEditCommand(sublime_plugin.TextCommand):
    """Prompt for instruction and rewrite selected code inline."""

    def run(self, edit):
        view = self.view
        window = view.window()
        if not window:
            return

        settings = sublime.load_settings("CodeContinue.sublime-settings")
        endpoint = settings.get("endpoint", "")
        model = settings.get("model", "")
        timeout_ms = settings.get("timeout_ms", 30000) / 1000.0

        if not is_endpoint_configured(settings):
            sublime.status_message("CodeContinue: Endpoint not configured.")
            sublime.set_timeout(lambda: show_endpoint_config_panel(view), 100)
            return

        if not endpoint or not model:
            sublime.status_message("CodeContinue: Endpoint or model not configured.")
            return

        selected_text = ""
        for region in view.sel():
            if not region.empty():
                selected_text += view.substr(region) + "\n"

        selected_text = selected_text.strip()
        if not selected_text:
            sublime.status_message("CodeContinue: No text selected for editing")
            return

        def on_done(instruction):
            if not instruction:
                return

            sublime.status_message("CodeContinue: Editing...")

            def do_api_call():
                prompt = (
                    "Rewrite the following code based on this instruction: {0}\n\n"
                    "Code:\n{1}"
                ).format(instruction, selected_text)

                data = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a code refactoring expert. Output ONLY the rewritten code without any markdown formatting, backticks, explanations, comments, or inline comments (unless requested by the user). Write clean code."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 2048,
                    "temperature": 0.3
                }

                _log("Edit: Sending request to {0}".format(endpoint))
                try:
                    req = urllib.request.Request(
                        endpoint,
                        data=json.dumps(data).encode(),
                        headers=build_api_headers(settings),
                    )
                    with urllib.request.urlopen(req, timeout=timeout_ms) as response:
                        result = json.loads(response.read().decode())
                        reply = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

                        if reply:
                            reply = clean_markdown_fences(reply)
                            sublime.set_timeout(lambda: view.run_command("code_continue_replace_selection", {"text": reply}), 0)
                            sublime.set_timeout(lambda: sublime.status_message("CodeContinue: Edit applied"), 0)
                        else:
                            sublime.set_timeout(lambda: sublime.status_message("CodeContinue: Empty response from model"), 0)

                except urllib.error.URLError as e:
                    _log_error("Edit: Network error: {0}".format(str(e)[:200]))
                    sublime.set_timeout(lambda: sublime.status_message("CodeContinue: Network error - {0}".format(str(e)[:50])), 0)
                except Exception as e:
                    _log_error("Edit: Error: {0}".format(str(e)[:200]))
                    sublime.set_timeout(lambda: sublime.status_message("CodeContinue: Error - {0}".format(str(e)[:50])), 0)

            threading.Thread(target=do_api_call, daemon=True).start()

        window.show_input_panel("Instruction:", "", on_done, None, None)

    def is_enabled(self):
        for region in self.view.sel():
            if not region.empty():
                return True
        return False


class CodeContinueReplaceSelectionCommand(sublime_plugin.TextCommand):
    """Helper command to replace the selection with text."""

    def run(self, edit, text=""):
        if not text:
            return

        regions = list(self.view.sel())
        regions.reverse()
        for region in regions:
            if not region.empty():
                self.view.replace(edit, region, text)

"""Inline edit / refactor feature: Prompts for instruction and replaces selection."""

import json
import os
import threading
import urllib.error
import urllib.request

import sublime
import sublime_plugin

from .api import get_provider
from .log import _log, _log_error
from .text_utils import clean_markdown_fences, compute_unified_diff
from .settings import is_endpoint_configured, show_endpoint_config_panel, get_feature_settings


def _set_diff_syntax(view):
    """Assign Diff syntax highlighting if available."""
    for syntax in ["Packages/Diff/Diff.sublime-syntax", "Packages/Diff/Diff.tmLanguage"]:
        try:
            if hasattr(view, "assign_syntax"):
                view.assign_syntax(syntax)
                return
            elif hasattr(view, "set_syntax_file"):
                view.set_syntax_file(syntax)
                return
        except Exception:
            continue


class CodeContinueEditCommand(sublime_plugin.TextCommand):
    """Prompt for instruction (or use preset) and rewrite selected code inline."""

    def run(self, edit, instruction=None):
        view = self.view
        window = view.window()
        if not window:
            return

        raw_settings = sublime.load_settings("CodeContinue.sublime-settings")
        settings = get_feature_settings(raw_settings, "edit")
        endpoint = settings.get("endpoint", "")
        model = settings.get("model", "")
        timeout_ms = settings.get("timeout_ms", 30000) / 1000.0
        confirm_edits = settings.get("confirm_edits", True)

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

        # Mark target regions so focus changes or diff viewing won't lose the selection
        view.add_regions(
            "code_continue_edit_target",
            [r for r in view.sel() if not r.empty()],
            "comment",
            "",
            sublime.DRAW_NO_FILL
        )

        def execute_edit(user_instruction):
            if not user_instruction:
                view.erase_regions("code_continue_edit_target")
                return

            sublime.status_message("CodeContinue: Editing...")

            def do_api_call():
                prompt = (
                    "Rewrite the following code based on this instruction: {0}\n\n"
                    "Code:\n{1}"
                ).format(user_instruction, selected_text)

                messages = [
                    {"role": "system", "content": "You are a code refactoring expert. Output ONLY the rewritten code without any markdown formatting, backticks, explanations, comments, or inline comments (unless requested by the user). Write clean code."},
                    {"role": "user", "content": prompt}
                ]
                
                provider = get_provider(endpoint, settings)
                data = provider.format_payload(model, messages, 2048, 0.3)

                _log("Edit: Sending request to {0}".format(endpoint))
                try:
                    req = urllib.request.Request(
                        endpoint,
                        data=json.dumps(data).encode(),
                        headers=provider.build_headers(settings),
                    )
                    with urllib.request.urlopen(req, timeout=timeout_ms) as response:
                        result = json.loads(response.read().decode())
                        reply = provider.parse_response(result)

                        if reply:
                            reply = clean_markdown_fences(reply)
                            sublime.set_timeout(lambda: handle_reply(reply, user_instruction), 0)
                        else:
                            view.erase_regions("code_continue_edit_target")
                            sublime.set_timeout(lambda: sublime.status_message("CodeContinue: Empty response from model"), 0)

                except urllib.error.URLError as e:
                    _log_error("Edit: Network error: {0}".format(str(e)[:200]))
                    view.erase_regions("code_continue_edit_target")
                    sublime.set_timeout(lambda: sublime.status_message("CodeContinue: Network error - {0}".format(str(e)[:50])), 0)
                except Exception as e:
                    _log_error("Edit: Error: {0}".format(str(e)[:200]))
                    view.erase_regions("code_continue_edit_target")
                    sublime.set_timeout(lambda: sublime.status_message("CodeContinue: Error - {0}".format(str(e)[:50])), 0)

            threading.Thread(target=do_api_call, daemon=True).start()

        def handle_reply(reply, user_instruction):
            if not confirm_edits:
                view.run_command("code_continue_replace_selection", {"text": reply})
                sublime.status_message("CodeContinue: Edit applied")
                return

            # Interactive Quick Panel
            filename = os.path.basename(view.file_name() or "code")
            items = [
                ["✓ Apply Edit", "Replace selection with generated code"],
                ["🔍 Preview Diff", "Inspect unified diff in a new tab before applying"],
                ["✗ Discard Edit", "Cancel without modifying selection"]
            ]

            def on_choice(index):
                if index == 0:  # Apply
                    view.run_command("code_continue_replace_selection", {"text": reply})
                    sublime.status_message("CodeContinue: Edit applied")
                elif index == 1:  # Preview Diff
                    show_diff_preview(reply, filename, user_instruction)
                else:  # Discard or Esc
                    view.erase_regions("code_continue_edit_target")
                    sublime.status_message("CodeContinue: Edit discarded")

            window.show_quick_panel(items, on_choice)

        def show_diff_preview(reply, filename, user_instruction):
            diff_text = compute_unified_diff(selected_text, reply, filename)
            diff_view = window.new_file()
            diff_view.set_scratch(True)
            diff_view.set_name("Diff: {0}".format(filename))
            header = "# CodeContinue Edit Diff: {0}\n# Instruction: {1}\n\n".format(filename, user_instruction)
            diff_view.run_command("append", {"characters": header + (diff_text or "# No textual differences\n")})
            _set_diff_syntax(diff_view)

            # Follow up with confirmation panel
            diff_items = [
                ["✓ Apply This Diff", "Accept changes and replace original code"],
                ["✗ Close & Discard", "Close diff tab and keep original code"]
            ]

            def on_diff_choice(idx):
                if idx == 0:  # Apply
                    if diff_view.is_valid():
                        diff_view.close()
                    window.focus_view(view)
                    view.run_command("code_continue_replace_selection", {"text": reply})
                    sublime.status_message("CodeContinue: Edit applied")
                else:
                    if diff_view.is_valid():
                        diff_view.close()
                    window.focus_view(view)
                    view.erase_regions("code_continue_edit_target")
                    sublime.status_message("CodeContinue: Edit discarded")

            window.show_quick_panel(diff_items, on_diff_choice)

        if instruction:
            execute_edit(instruction)
        else:
            window.show_input_panel("Instruction:", "", execute_edit, None, lambda: view.erase_regions("code_continue_edit_target"))

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

        regions = self.view.get_regions("code_continue_edit_target")
        self.view.erase_regions("code_continue_edit_target")
        if not regions:
            regions = list(self.view.sel())

        regions.reverse()
        for region in regions:
            if not region.empty():
                self.view.replace(edit, region, text)


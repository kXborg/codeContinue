"""Inline-suggestion flow: phantom rendering, Enter-trigger, accept command.

State is kept in module-level dicts keyed on `view.id()`. Sublime calls the
EventListener / TextCommand classes here directly, but only because
codeContinue.py imports them into the top-level package namespace.
"""

import html
import json
import threading
import time
import urllib.error
import urllib.request

import sublime
import sublime_plugin

from .api import build_api_headers
from .log import _log, _log_error
from .settings import is_endpoint_configured, show_endpoint_config_panel
from .text_utils import clean_markdown_fences, strip_common_indent


# view.id() -> (PhantomSet, [normalized_lines], common_prefix)
phantoms = {}
# view.id() -> seconds since epoch of last suggest request (rate-limit gate)
last_request_time = {}
# view.id() -> request_id, used to ignore stale responses
pending_requests = {}
# view.id() set: phantom-clearing is suppressed while we're inserting
suppress_clear = set()
# view.id() -> wall-clock deadline. While `time.time() < deadline`, on_modified
# won't clear the phantom — gives the accept command time to settle.
accept_grace_until = {}


class CodeContinueListener(sublime_plugin.EventListener):
    def on_modified(self, view):
        # Clear any phantom suggestion when the user modifies text
        # (skip clearing if we're currently accepting a suggestion).
        vid = view.id()
        if vid in phantoms:
            if vid in suppress_clear:
                return
            grace = accept_grace_until.get(vid, 0)
            if time.time() < grace:
                return
            clear_phantoms(view)
        return

    def on_text_command(self, view, command_name, args):
        """Trigger suggestion when the user inserts a newline (presses Enter)."""
        settings = sublime.load_settings("CodeContinue.sublime-settings")
        trigger_langs = settings.get("trigger_language", [])
        if not view.syntax():
            return
        if view.syntax().name.lower() not in [lang.lower() for lang in trigger_langs]:
            return

        if command_name == "insert" and args and args.get("characters") == "\n":
            _log("Enter pressed; evaluating trigger")
            existing = phantoms.get(view.id())
            if existing and isinstance(existing[1], list) and len(existing[1]) > 0:
                _log("Enter ignored because cached suggestion exists")
                return
            vid = view.id()
            if vid in phantoms:
                _log("Enter ignored because phantom already visible")
                return
            now = time.time()
            last = last_request_time.get(vid, 0)
            if now - last < 1.0:
                _log("Enter ignored due to rate limit <1000ms")
                return
            last_request_time[vid] = now
            # Slight delay so the cursor has moved to the new line
            sublime.set_timeout(lambda: view.run_command("code_continue_suggest"), 50)


class CodeContinueSuggestCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        settings = sublime.load_settings("CodeContinue.sublime-settings")
        endpoint = settings.get("endpoint", "")
        model = settings.get("model", "")
        max_lines = settings.get("max_context_lines", 40)
        timeout_ms = settings.get("timeout_ms", 30000) / 1000.0  # seconds

        if not is_endpoint_configured(settings):
            sublime.status_message("CodeContinue: Endpoint not configured. Opening configuration...")
            sublime.set_timeout(lambda: show_endpoint_config_panel(view), 100)
            return

        if not endpoint or not model:
            sublime.status_message("CodeContinue: Endpoint or model not configured.")
            return

        sel = view.sel()
        if len(sel) != 1:
            return
        cursor = sel[0].begin()

        # Build context: extract N lines around the cursor.
        cursor_row, _cursor_col = view.rowcol(cursor)
        lines_before = max_lines // 2
        lines_after = max_lines // 2

        total_lines = view.rowcol(view.size())[0] + 1
        start_row = max(0, cursor_row - lines_before)
        end_row = min(total_lines, cursor_row + lines_after + 1)

        start_point = view.text_point(start_row, 0)
        end_point = view.text_point(end_row, 0) if end_row < total_lines else view.size()
        code = view.substr(sublime.Region(start_point, end_point))

        cursor_offset = cursor - start_point
        code_before = code[:cursor_offset]
        prompt = "Continue the following code:\n{0}".format(code_before)

        vid = view.id()
        request_id = (vid, cursor, time.time())
        pending_requests[vid] = request_id

        sublime.status_message("CodeContinue: Fetching suggestion...")

        def fetch_completion():
            request_start_time = time.time()
            try:
                if pending_requests.get(vid) != request_id:
                    return

                data = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a code completion expert. Output ONLY the code continuation without any markdown formatting, backticks, explanations, comments, or inline comments. Write clean code without any commentary. Do NOT include the <CURSOR_HERE> marker in your response."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1024,
                    "temperature": 0.3
                }
                _log("Sending request to endpoint {0} (timeout: {1:.1f}s)".format(endpoint, timeout_ms))
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(data).encode(),
                    headers=build_api_headers(settings),
                )
                response_start_time = time.time()
                with urllib.request.urlopen(req, timeout=timeout_ms) as response:
                    response_received_time = time.time()
                    result = json.loads(response.read().decode())
                    _log("Received Response : {}".format(result))
                    completion = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    parse_complete_time = time.time()

                    response_time = response_received_time - response_start_time
                    parse_time = parse_complete_time - response_received_time
                    total_time = parse_complete_time - request_start_time
                    _log("Response received: {0:.2f}s (network), {1:.3f}s (parse), total {2:.2f}s".format(response_time, parse_time, total_time))

                    completion = clean_markdown_fences(completion)

                    if pending_requests.get(vid) == request_id and completion:
                        sublime.set_timeout(lambda: show_phantom(view, cursor, completion), 0)
                    elif pending_requests.get(vid) == request_id:
                        sublime.set_timeout(lambda: sublime.status_message("CodeContinue: Empty response"), 0)
            except urllib.error.URLError as e:
                elapsed = time.time() - request_start_time
                _log_error("Network error after {0:.2f}s: {1}".format(elapsed, str(e)[:200]))
                if pending_requests.get(vid) == request_id:
                    msg = "CodeContinue: Network error - {0}".format(str(e)[:50])
                    sublime.set_timeout(lambda: sublime.status_message(msg), 0)
            except (ValueError, KeyError) as e:
                elapsed = time.time() - request_start_time
                _log_error("Parse error after {0:.2f}s: {1}".format(elapsed, str(e)[:200]))
                if pending_requests.get(vid) == request_id:
                    msg = "CodeContinue: Parse error - {0}".format(str(e)[:50])
                    sublime.set_timeout(lambda: sublime.status_message(msg), 0)
            except Exception as e:
                elapsed = time.time() - request_start_time
                _log_error("Unexpected error after {0:.2f}s: {1}".format(elapsed, str(e)[:200]))
                if pending_requests.get(vid) == request_id:
                    msg = "CodeContinue: Unexpected error - {0}".format(str(e)[:50])
                    sublime.set_timeout(lambda: sublime.status_message(msg), 0)

        threading.Thread(target=fetch_completion, daemon=True).start()


class CodeContinueAcceptCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        vid = view.id()
        if vid not in phantoms:
            return

        phantom_set, remaining, common_prefix = phantoms[vid]
        if not isinstance(remaining, list) or len(remaining) == 0:
            clear_phantoms(view)
            return

        sel = view.sel()
        if len(sel) != 1:
            clear_phantoms(view)
            return

        suppress_clear.add(vid)
        try:
            insert_pos = sel[0].begin()

            first_line = remaining.pop(0)

            # Remaining lines were normalised (common indent stripped) by show_phantom.
            # After we insert "\n" the cursor moves to column 0, so re-apply the
            # stripped prefix to restore each remaining line's original column.
            rem_lines = remaining
            if rem_lines and common_prefix:
                rem_lines = [common_prefix + ln for ln in rem_lines]
                common_prefix = ""

            text_to_insert = first_line
            if rem_lines:
                text_to_insert += "\n"

            view.insert(edit, insert_pos, text_to_insert)

            new_cursor = insert_pos + len(text_to_insert)
            view.sel().clear()
            view.sel().add(sublime.Region(new_cursor, new_cursor))

            if rem_lines:
                preview = "\n".join(rem_lines)
                ph = phantom_set
                ph.update([sublime.Phantom(
                    sublime.Region(new_cursor, new_cursor),
                    '<span style="color: gray">{0}</span>'.format(html.escape(preview)),
                    sublime.LAYOUT_INLINE,
                )])
                phantoms[vid] = (ph, rem_lines, common_prefix)
                view.set_status('code_continue_visible', 'true')
            else:
                clear_phantoms(view)
        finally:
            # Keep a short grace window to avoid immediate on_modified clearing
            accept_grace_until[vid] = time.time() + 0.2
            if vid in suppress_clear:
                suppress_clear.remove(vid)


def show_phantom(view, cursor, suggestion):
    clear_phantoms(view)
    phantom_set = sublime.PhantomSet(view)

    lines = suggestion.split('\n')
    if len(lines) > 0 and lines[-1] == "":
        lines = lines[:-1]

    norm_lines, common_prefix = strip_common_indent(lines)

    preview = "\n".join(norm_lines)
    if not preview:
        return

    phantom = sublime.Phantom(
        sublime.Region(cursor, cursor),
        '<span style="color: gray">{0}</span>'.format(html.escape(preview)),
        sublime.LAYOUT_INLINE,
    )
    phantom_set.update([phantom])
    phantoms[view.id()] = (phantom_set, norm_lines, common_prefix)
    view.set_status('code_continue_visible', 'true')


def clear_phantoms(view):
    if view.id() in phantoms:
        phantoms[view.id()][0].update([])
        del phantoms[view.id()]
    view.erase_status('code_continue_visible')

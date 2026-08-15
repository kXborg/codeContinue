"""Inline-suggestion flow: phantom rendering, Enter-trigger, accept command.

State is kept in a SuggestState class keyed on `view.id()`. Sublime calls the
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

from .api import get_provider
from .log import _log, _log_error
from .settings import is_endpoint_configured, show_endpoint_config_panel
from .text_utils import clean_markdown_fences, strip_common_indent


class SuggestState:
    """Per-view state for the inline-suggestion flow.

    Replaces the former module-level dicts/sets (``phantoms``,
    ``last_request_time``, ``pending_requests``, ``suppress_clear``,
    ``accept_grace_until``).  Accessed via the module-level ``_states`` dict,
    keyed on ``view.id()``.
    """

    __slots__ = (
        "phantom_set",
        "remaining_lines",
        "common_prefix",
        "last_request_time",
        "pending_request_id",
        "suppress_clear",
        "accept_grace_until",
    )

    def __init__(self):
        self.phantom_set = None        # sublime.PhantomSet or None
        self.remaining_lines = None    # [str] or None
        self.common_prefix = ""        # stripped indent prefix
        self.last_request_time = 0.0   # wall-clock timestamp of last request
        self.pending_request_id = None # (vid, cursor, timestamp) or None
        self.suppress_clear = False    # True while an accept is in-flight
        self.accept_grace_until = 0.0  # wall-clock deadline

    @property
    def has_phantom(self):
        return self.phantom_set is not None


# view.id() -> SuggestState
_states = {}


def _get_state(vid):
    """Return the SuggestState for *vid*, creating one if needed."""
    if vid not in _states:
        _states[vid] = SuggestState()
    return _states[vid]


def _drop_state(vid):
    """Remove all state for *vid* (e.g. after phantoms are cleared)."""
    _states.pop(vid, None)


LANGUAGE_ALIASES = {
    "cpp": {"cpp", "c++", "c"},
    "c++": {"cpp", "c++", "c"},
    "javascript": {"javascript", "js"},
    "js": {"javascript", "js"},
    "typescript": {"typescript", "ts"},
    "ts": {"typescript", "ts"},
    "python": {"python", "py"},
    "py": {"python", "py"},
}


def is_syntax_supported(syntax, trigger_langs):
    """Check if the given sublime.Syntax matches configured trigger_langs."""
    if not syntax or not trigger_langs:
        return False

    trigger_set = {str(l).strip().lower() for l in trigger_langs}
    if "*" in trigger_set or "all" in trigger_set:
        return True

    syntax_name = getattr(syntax, "name", "").lower()
    syntax_scope = getattr(syntax, "scope", "").lower()

    for lang in trigger_set:
        if lang in syntax_name or lang in syntax_scope:
            return True
        aliases = LANGUAGE_ALIASES.get(lang, set())
        if any(alias in syntax_name or alias in syntax_scope for alias in aliases):
            return True

    return False


class CodeContinueListener(sublime_plugin.EventListener):
    def on_modified(self, view):
        # Clear any phantom suggestion when the user modifies text
        # (skip clearing if we're currently accepting a suggestion).
        vid = view.id()
        state = _states.get(vid)
        if state and state.has_phantom:
            if state.suppress_clear:
                return
            if time.time() < state.accept_grace_until:
                return
            clear_phantoms(view)
        return

    def on_text_command(self, view, command_name, args):
        """Trigger suggestion when the user inserts a newline (presses Enter)."""
        settings = sublime.load_settings("CodeContinue.sublime-settings")
        trigger_langs = settings.get("trigger_language", [])
        if not is_syntax_supported(view.syntax(), trigger_langs):
            return

        if command_name == "insert" and args and args.get("characters") == "\n":
            _log("Enter pressed; evaluating trigger")
            vid = view.id()
            state = _states.get(vid)
            if state and state.has_phantom:
                if state.remaining_lines and len(state.remaining_lines) > 0:
                    _log("Enter ignored because cached suggestion exists")
                    return
                _log("Enter ignored because phantom already visible")
                return
            now = time.time()
            st = _get_state(vid)
            if now - st.last_request_time < 1.0:
                _log("Enter ignored due to rate limit <1000ms")
                return
            st.last_request_time = now
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
        state = _get_state(vid)
        request_id = (vid, cursor, time.time())
        state.pending_request_id = request_id

        sublime.status_message("CodeContinue: Fetching suggestion...")

        def fetch_completion():
            request_start_time = time.time()
            try:
                if state.pending_request_id != request_id:
                    return

                _DEFAULT_SYSTEM_PROMPT = (
                    "You are a code completion expert. Output ONLY the code continuation "
                    "without any markdown formatting, backticks, explanations, comments, or "
                    "inline comments. Write clean code without any commentary. "
                    "Do NOT include the <CURSOR_HERE> marker in your response."
                )
                system_prompt = settings.get("system_prompt", "").strip() or _DEFAULT_SYSTEM_PROMPT
                _log("Using system prompt: {0}".format(system_prompt[:120]))

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
                provider = get_provider(endpoint, settings)
                data = provider.format_payload(model, messages, 1024, 0.3)

                _log("Sending request to endpoint {0} (timeout: {1:.1f}s)".format(endpoint, timeout_ms))
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(data).encode(),
                    headers=provider.build_headers(settings),
                )
                response_start_time = time.time()
                with urllib.request.urlopen(req, timeout=timeout_ms) as response:
                    response_received_time = time.time()
                    raw_body = response.read().decode()
                    _log("Raw response body: {0}".format(raw_body[:2000]))
                    result = json.loads(raw_body)
                    _log("Parsed response: {}".format(result))
                    completion = provider.parse_response(result)
                    parse_complete_time = time.time()

                    response_time = response_received_time - response_start_time
                    parse_time = parse_complete_time - response_received_time
                    total_time = parse_complete_time - request_start_time
                    _log("Response received: {0:.2f}s (network), {1:.3f}s (parse), total {2:.2f}s".format(response_time, parse_time, total_time))

                    completion = clean_markdown_fences(completion)

                    if state.pending_request_id == request_id and completion:
                        sublime.set_timeout(lambda: show_phantom(view, cursor, completion), 0)
                    elif state.pending_request_id == request_id:
                        sublime.set_timeout(lambda: sublime.status_message("CodeContinue: Empty response"), 0)
            except urllib.error.URLError as e:
                elapsed = time.time() - request_start_time
                _log_error("Network error after {0:.2f}s: {1}".format(elapsed, str(e)[:200]))
                if state.pending_request_id == request_id:
                    msg = "CodeContinue: Network error - {0}".format(str(e)[:50])
                    sublime.set_timeout(lambda: sublime.status_message(msg), 0)
            except (ValueError, KeyError) as e:
                elapsed = time.time() - request_start_time
                _log_error("Parse error after {0:.2f}s: {1}".format(elapsed, str(e)[:200]))
                try:
                    _log_error("Raw body that failed to parse: {0}".format(raw_body[:2000]))
                except NameError:
                    pass  # raw_body not set; error occurred before read()
                if state.pending_request_id == request_id:
                    msg = "CodeContinue: Parse error - {0}".format(str(e)[:50])
                    sublime.set_timeout(lambda: sublime.status_message(msg), 0)
            except Exception as e:
                elapsed = time.time() - request_start_time
                _log_error("Unexpected error after {0:.2f}s: {1}".format(elapsed, str(e)[:200]))
                if state.pending_request_id == request_id:
                    msg = "CodeContinue: Unexpected error - {0}".format(str(e)[:50])
                    sublime.set_timeout(lambda: sublime.status_message(msg), 0)

        threading.Thread(target=fetch_completion, daemon=True).start()


class CodeContinueAcceptCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        vid = view.id()
        state = _states.get(vid)
        if not state or not state.has_phantom:
            return

        remaining = state.remaining_lines
        if not isinstance(remaining, list) or len(remaining) == 0:
            clear_phantoms(view)
            return

        sel = view.sel()
        if len(sel) != 1:
            clear_phantoms(view)
            return

        state.suppress_clear = True
        try:
            insert_pos = sel[0].begin()

            first_line = remaining.pop(0)

            # Remaining lines were normalised (common indent stripped) by show_phantom.
            # After we insert "\n" the cursor moves to column 0, so re-apply the
            # stripped prefix to restore each remaining line's original column.
            rem_lines = remaining
            if rem_lines and state.common_prefix:
                rem_lines = [state.common_prefix + ln for ln in rem_lines]
                state.common_prefix = ""

            text_to_insert = first_line
            if rem_lines:
                text_to_insert += "\n"

            view.insert(edit, insert_pos, text_to_insert)

            new_cursor = insert_pos + len(text_to_insert)
            view.sel().clear()
            view.sel().add(sublime.Region(new_cursor, new_cursor))

            if rem_lines:
                preview = "\n".join(rem_lines)
                ph = state.phantom_set
                ph.update([sublime.Phantom(
                    sublime.Region(new_cursor, new_cursor),
                    '<span style="color: gray">{0}</span>'.format(html.escape(preview)),
                    sublime.LAYOUT_INLINE,
                )])
                state.remaining_lines = rem_lines
                view.set_status('code_continue_visible', 'true')
            else:
                clear_phantoms(view)
        finally:
            # Keep a short grace window to avoid immediate on_modified clearing
            state.accept_grace_until = time.time() + 0.2
            state.suppress_clear = False


def show_phantom(view, cursor, suggestion):
    clear_phantoms(view)
    vid = view.id()
    state = _get_state(vid)

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

    state.phantom_set = phantom_set
    state.remaining_lines = norm_lines
    state.common_prefix = common_prefix
    view.set_status('code_continue_visible', 'true')


def clear_phantoms(view):
    vid = view.id()
    state = _states.get(vid)
    if state and state.has_phantom:
        state.phantom_set.update([])
    _drop_state(vid)
    view.erase_status('code_continue_visible')

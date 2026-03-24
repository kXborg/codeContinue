import sublime
import sublime_plugin
import threading
import json
import urllib.request
import urllib.error
import time
import re

# Simple logger with timestamp to stdout (only when debug is enabled)
def _log(msg):
    settings = sublime.load_settings("CodeContinue.sublime-settings")
    if settings.get("debug", False):
        ts = time.strftime('%H:%M:%S')
        print("CodeContinue [{0}] {1}".format(ts, msg))


def clean_markdown_fences(text):
    """
    Remove markdown code fence markers and special tokens from LLM output.
    Handles patterns like:
    - ```python\ncode\n```
    - ```\ncode\n```
    - code```  (trailing fence)
    - [END_OF_TEXT] token
    
    Called once per API response for efficiency.
    """
    if not text:
        return text
    
    # Pattern for opening fence: ```language or just ```
    # Match at start of string (with optional whitespace)
    opening_pattern = r'^\s*```[\w]*\s*\n?'
    text = re.sub(opening_pattern, '', text)
    
    # Pattern for closing fence: ```
    # Match at end of string (with optional whitespace)
    closing_pattern = r'\n?\s*```\s*$'
    text = re.sub(closing_pattern, '', text)
    
    # Remove special tokens like [END_OF_TEXT], [INST], etc.
    text = re.sub(r'\[END_OF_TEXT\]', '', text)
    text = re.sub(r'\[INST\]', '', text)
    text = re.sub(r'\[/INST\]', '', text)
    
    # Strip any remaining leading/trailing whitespace
    text = text.strip()
    
    return text


def is_endpoint_configured(settings):
    """Check if endpoint is properly configured (not placeholder)."""
    endpoint = settings.get("endpoint", "").strip()
    if not endpoint or "your-api" in endpoint.lower():
        return False
    return True


def show_endpoint_config_panel(view):
    """Show input panel to configure endpoint on first run."""
    settings = sublime.load_settings("CodeContinue.sublime-settings")
    current_endpoint = settings.get("endpoint", "https://your-api.com/v1/chat/completions")
    
    def on_endpoint_done(endpoint_text):
        if endpoint_text.strip():
            settings.set("endpoint", endpoint_text.strip())
            
            # Now ask for model
            current_model = settings.get("model", "gpt-3.5-turbo")
            def on_model_done(model_text):
                if model_text.strip():
                    settings.set("model", model_text.strip())
                    sublime.save_settings("CodeContinue.sublime-settings")
                    sublime.status_message("CodeContinue: Configuration saved! Ready to use.")
                    _log("Configuration saved: endpoint and model set")
            
            view.window().show_input_panel(
                "CodeContinue - Model name:",
                current_model,
                on_model_done,
                None,
                None
            )
        else:
            sublime.status_message("CodeContinue: Endpoint not configured. Run 'CodeContinue: Configure' to set it up.")
    
    view.window().show_input_panel(
        "CodeContinue - API Endpoint URL:",
        current_endpoint,
        on_endpoint_done,
        None,
        None
    )


# Global dict to store phantoms per view
# Each entry: view.id() -> (phantom_set, [normalized_lines])
phantoms = {}
# Cache for last context to reuse
last_context = {}
# Per-view timestamp of last request (seconds since epoch)
last_request_time = {}
# Per-view pending request ID to deduplicate/cancel stale requests
pending_requests = {}
# Views for which phantom-clearing is temporarily suppressed (e.g. during accept)
suppress_clear = set()
# Grace period after accept during which on_modified won't clear phantoms
accept_grace_until = {}


class CodeContinueListener(sublime_plugin.EventListener):
    def on_modified(self, view):
        # Clear any phantom suggestion when the user modifies text
        # (skip clearing if we're currently accepting a suggestion)
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
        """Trigger suggestion when the user inserts a newline (presses Enter).
        This provides a simple, fast trigger for next-line suggestions.
        """
        # Only trigger for configured languages
        settings = sublime.load_settings("CodeContinue.sublime-settings")
        trigger_langs = settings.get("trigger_language", [])
        if not view.syntax():
            return
        if view.syntax().name.lower() not in [lang.lower() for lang in trigger_langs]:
            return

        # Detect Enter insertion
        if command_name == "insert" and args and args.get("characters") == "\n":
            _log("Enter pressed; evaluating trigger")
            # If we already have a pending suggestion with remaining lines, do not re-request
            existing = phantoms.get(view.id())
            if existing and isinstance(existing[1], list) and len(existing[1]) > 0:
                _log("Enter ignored because cached suggestion exists")
                return
            # Rate-limit: ensure at least 1000 ms between requests per view
            vid = view.id()
            # If a phantom suggestion already exists for this view, don't send another request
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

    def _auto_suggest(self, view):
        if view.is_scratch() or not view.window():
            return
        # Clear existing phantoms
        clear_phantoms(view)
        # Trigger suggest
        view.run_command("code_continue_suggest")


class CodeContinueSuggestCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        settings = sublime.load_settings("CodeContinue.sublime-settings")
        endpoint = settings.get("endpoint", "")
        model = settings.get("model", "")
        max_lines = settings.get("max_context_lines", 40)
        timeout_ms = settings.get("timeout_ms", 150) / 1000.0  # Convert to seconds

        # Check if endpoint is configured
        if not is_endpoint_configured(settings):
            sublime.status_message("CodeContinue: Endpoint not configured. Opening configuration...")
            sublime.set_timeout(lambda: show_endpoint_config_panel(view), 100)
            return
        
        if not endpoint or not model:
            sublime.status_message("CodeContinue: Endpoint or model not configured.")
            return

        # Get cursor position
        sel = view.sel()
        if len(sel) != 1:
            return
        cursor = sel[0].begin()

        # Get context: extract N lines before and after cursor (by line number, not char offset)
        cursor_row, cursor_col = view.rowcol(cursor)
        lines_before = max_lines // 2
        lines_after = max_lines // 2
        
        # Get total line count from the end of file
        total_lines = view.rowcol(view.size())[0] + 1
        
        start_row = max(0, cursor_row - lines_before)
        end_row = min(total_lines, cursor_row + lines_after + 1)
        
        # Get the region spanning those lines
        start_point = view.text_point(start_row, 0)
        end_point = view.text_point(end_row, 0) if end_row < total_lines else view.size()
        context_region = sublime.Region(start_point, end_point)
        code = view.substr(context_region)

        # Build prompt without special markers that might confuse the model
        cursor_offset = cursor - start_point
        code_before = code[:cursor_offset]
        code_after = code[cursor_offset:]
        prompt = "Continue the following code:\n{0}".format(code_before)

        # Generate unique request ID for this view/cursor
        vid = view.id()
        request_id = (vid, cursor, time.time())
        pending_requests[vid] = request_id
        
        sublime.status_message("CodeContinue: Fetching suggestion...")
        
        # Async API call
        def fetch_completion():
            request_start_time = time.time()
            try:
                # Check if this request is still relevant
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
                req = urllib.request.Request(endpoint, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
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
                    
                    # Clean markdown code fences (once per response, before processing)
                    completion = clean_markdown_fences(completion)
                    
                    # Verify request is still relevant after network call
                    if pending_requests.get(vid) == request_id and completion:
                        # Show phantom
                        sublime.set_timeout(lambda: show_phantom(view, cursor, completion), 0)
                    elif pending_requests.get(vid) == request_id:
                        sublime.status_message("CodeContinue: Empty response")
            except urllib.error.URLError as e:
                elapsed = time.time() - request_start_time
                _log("Network error after {0:.2f}s: {1}".format(elapsed, str(e)[:100]))
                if pending_requests.get(vid) == request_id:
                    sublime.status_message("CodeContinue: Network error - {0}".format(str(e)[:50]))
            except (ValueError, KeyError) as e:
                elapsed = time.time() - request_start_time
                _log("Parse error after {0:.2f}s: {1}".format(elapsed, str(e)[:100]))
                if pending_requests.get(vid) == request_id:
                    sublime.status_message("CodeContinue: Parse error - {0}".format(str(e)[:50]))
            except Exception as e:
                elapsed = time.time() - request_start_time
                _log("Unexpected error after {0:.2f}s: {1}".format(elapsed, str(e)[:100]))
                if pending_requests.get(vid) == request_id:
                    sublime.status_message("CodeContinue: Unexpected error - {0}".format(str(e)[:50]))

        threading.Thread(target=fetch_completion).start()


class CodeContinueAcceptCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        vid = view.id()
        if vid not in phantoms:
            return

        phantom_set, remaining = phantoms[vid]
        # remaining is expected to be a list of suggestion lines
        if not isinstance(remaining, list) or len(remaining) == 0:
            clear_phantoms(view)
            return

        sel = view.sel()
        if len(sel) != 1:
            clear_phantoms(view)
            return

        # Prevent on_modified from clearing the phantom while we insert
        suppress_clear.add(vid)
        try:
            insert_pos = sel[0].begin()

            # Prepare line to insert (first line)
            first_line = remaining.pop(0)

            # Remaining lines are already normalized (common indent stripped) by show_phantom
            rem_lines = remaining

            # Insert first line at the cursor
            text_to_insert = first_line
            # If there are more lines, append a newline (without forcing indentation)
            if rem_lines:
                text_to_insert += "\n"

            view.insert(edit, insert_pos, text_to_insert)

            # Move cursor to end of inserted text
            new_cursor = insert_pos + len(text_to_insert)
            view.sel().clear()
            view.sel().add(sublime.Region(new_cursor, new_cursor))

            # If there are remaining lines, update phantom to show them and save state
            if rem_lines:
                # Build remaining suggestion preview (join with newline)
                preview = "\n".join(rem_lines)
                ph = phantom_set
                ph.update([sublime.Phantom(sublime.Region(new_cursor, new_cursor), '<span style="color: gray">{0}</span>'.format(preview), sublime.LAYOUT_INLINE)])
                phantoms[vid] = (ph, rem_lines)
                view.set_status('code_continue_visible', 'true')
            else:
                clear_phantoms(view)
        finally:
            # Keep a short grace window to avoid immediate on_modified clearing
            accept_grace_until[vid] = time.time() + 0.2
            if vid in suppress_clear:
                suppress_clear.remove(vid)

def show_phantom(view, cursor, suggestion):
    global phantoms
    clear_phantoms(view)
    phantom_set = sublime.PhantomSet(view)

    # Normalize suggestion into lines and strip common leading indent so it can be reindented
    lines = suggestion.split('\n')
    # If the suggestion ends with a trailing empty line, drop the final empty element
    if len(lines) > 0 and lines[-1] == "":
        lines = lines[:-1]

    # Compute common indent across non-empty lines
    def _strip_common_indent(lines_in):
        import re
        indents = []
        for ln in lines_in:
            if ln.strip() == "":
                continue
            m2 = re.match(r"^[ \t]*", ln)
            indents.append(m2.group(0))
        if not indents:
            return lines_in
        min_indent = min(len(x) for x in indents)
        return [ln[min_indent:] if len(ln) >= min_indent else ln for ln in lines_in]

    norm_lines = _strip_common_indent(lines)

    # Build preview text for the phantom
    preview = "\n".join(norm_lines)
    if not preview:
        return

    # Create phantom at cursor position showing the remaining suggestion
    phantom = sublime.Phantom(sublime.Region(cursor, cursor), '<span style="color: gray">{0}</span>'.format(preview), sublime.LAYOUT_INLINE)
    phantom_set.update([phantom])
    phantoms[view.id()] = (phantom_set, norm_lines)
    view.set_status('code_continue_visible', 'true')

def clear_phantoms(view):
    global phantoms
    if view.id() in phantoms:
        phantoms[view.id()][0].update([])
        del phantoms[view.id()]
    view.erase_status('code_continue_visible')


# Global to store endpoint during setup dialog flow
_setup_endpoint = None


def plugin_loaded():
    """Called when Sublime Text loads the plugin"""
    settings = sublime.load_settings("CodeContinue.sublime-settings")
    
    # Check if this is first run (settings are empty/not configured)
    endpoint = settings.get("endpoint", "").strip()
    model = settings.get("model", "").strip()
    
    if not endpoint or not model:
        _log("CodeContinue: First run detected, showing setup dialog")
        sublime.set_timeout(show_setup_dialog, 500)


def show_setup_dialog():
    """Show input panel for endpoint configuration"""
    window = sublime.active_window()
    if not window:
        return
    
    window.show_input_panel(
        "CodeContinue Setup: Enter your v1 API endpoint",
        "https://api.openai.com/v1/chat/completions",
        on_endpoint_entered,
        None,
        None
    )


def on_endpoint_entered(endpoint):
    """Callback after endpoint is entered"""
    global _setup_endpoint
    _setup_endpoint = endpoint
    window = sublime.active_window()
    if not window:
        return
    
    window.show_input_panel(
        "CodeContinue Setup: Enter your model name",
        "gpt-3.5-turbo",
        on_model_entered,
        None,
        None
    )


def on_model_entered(model):
    """Callback after model is entered, save both settings"""
    global _setup_endpoint
    
    if not _setup_endpoint:
        sublime.error_dialog("CodeContinue Setup Error: Endpoint not set")
        return
    
    settings = sublime.load_settings("CodeContinue.sublime-settings")
    settings.set("endpoint", _setup_endpoint)
    settings.set("model", model)
    sublime.save_settings("CodeContinue.sublime-settings")
    
    _log("CodeContinue: Configuration saved. Endpoint: {0}, Model: {1}".format(_setup_endpoint, model))
    sublime.message_dialog("CodeContinue configured successfully!\n\nEndpoint: {0}\nModel: {1}\n\nPress Ctrl+Enter to get a code suggestion.".format(_setup_endpoint, model))


class CodeContinueConfigureCommand(sublime_plugin.TextCommand):
    """Command to configure CodeContinue settings via Command Palette"""
    def run(self, edit):
        view = self.view
        settings = sublime.load_settings("CodeContinue.sublime-settings")
        
        # Endpoint panel
        current_endpoint = settings.get("endpoint", "https://your-api.com/v1/chat/completions")
        
        def on_endpoint_done(endpoint_text):
            if endpoint_text.strip():
                settings.set("endpoint", endpoint_text.strip())
                
                # Model panel
                current_model = settings.get("model", "gpt-3.5-turbo")
                def on_model_done(model_text):
                    if model_text.strip():
                        settings.set("model", model_text.strip())
                        
                        # API Key panel (optional)
                        current_api_key = settings.get("api_key", "")
                        def on_api_key_done(api_key_text):
                            settings.set("api_key", api_key_text.strip() if api_key_text.strip() else "")
                            sublime.save_settings("CodeContinue.sublime-settings")
                            sublime.status_message("CodeContinue: Configuration saved!")
                            _log("Configuration updated via Command Palette")
                        
                        view.window().show_input_panel(
                            "CodeContinue - API Key (optional, leave blank to skip):",
                            current_api_key,
                            on_api_key_done,
                            None,
                            None
                        )
                
                view.window().show_input_panel(
                    "CodeContinue - Model name:",
                    current_model,
                    on_model_done,
                    None,
                    None
                )
        
        view.window().show_input_panel(
            "CodeContinue - API Endpoint URL:",
            current_endpoint,
            on_endpoint_done,
            None,
            None
        )


# ─── Chat Feature ────────────────────────────────────────────────────────────

# Per-view chat state: chat_view.id() -> dict with history, settings, etc.
_chat_sessions = {}
# Track which views are chat views
_chat_view_ids = set()
# Store original layout to restore on close
_original_layouts = {}
# Flag to prevent re-entrant request sending
_chat_requesting = set()

CHAT_SYSTEM_PROMPT = (
    "You are a helpful code assistant. The user has selected a piece of code "
    "and wants to discuss it. Provide clear, concise explanations and suggestions. "
    "When showing code, use markdown formatting. Be direct and practical."
)

INPUT_SEPARATOR = "\n── Type below and press Enter to send (close tab to end) ──\n"


def _build_api_headers(settings):
    """Build request headers including Authorization if api_key is set."""
    headers = {"Content-Type": "application/json"}
    api_key = settings.get("api_key", "")
    if api_key:
        headers["Authorization"] = "Bearer {0}".format(api_key)
    return headers


def _chat_view_append(chat_view, text):
    """Append text to a chat view (thread-safe via set_timeout)."""
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
    was_read_only = chat_view.is_read_only()
    chat_view.set_read_only(False)
    chat_view.run_command("append", {"characters": INPUT_SEPARATOR})
    # Leave editable so user can type
    chat_view.run_command("move_to", {"to": "eof"})


def _chat_lock_and_format_input(chat_view, user_text):
    """Lock the view, replace the input area with a formatted user message."""
    content = chat_view.substr(sublime.Region(0, chat_view.size()))
    sep_pos = content.rfind(INPUT_SEPARATOR)
    if sep_pos < 0:
        return
    
    # Rebuild content: everything before separator + formatted user message
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
    """Send conversation history to LLM and show response in chat view."""
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
        "temperature": 0.5
    }
    
    _log("Chat: Sending request to {0}".format(endpoint))
    
    def do_request():
        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(data).encode(),
                headers=headers
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
    
    # Format input area into conversation
    _chat_lock_and_format_input(chat_view, user_text)
    
    # Add to history
    session["history"].append({"role": "user", "content": user_text})
    
    # Show thinking
    _chat_view_append(chat_view, "\n⏳ Thinking...\n")
    
    # Send request
    _chat_do_api_call(chat_view, session)


class ChatEventListener(sublime_plugin.EventListener):
    """Handle Enter key and view close in chat views."""
    
    def on_text_command(self, view, command_name, args):
        """Intercept Enter key in chat views to send message."""
        if view.id() not in _chat_view_ids:
            return None
        
        if command_name == "insert" and args and args.get("characters") == "\n":
            user_text = _chat_get_user_input(view)
            if user_text and view.id() not in _chat_requesting:
                _chat_send_message(view)
                return ("noop", None)
        
        return None
    
    def on_close(self, view):
        """Clean up when a chat view is closed and restore layout."""
        vid = view.id()
        if vid not in _chat_view_ids:
            return
        
        _chat_view_ids.discard(vid)
        _chat_sessions.pop(vid, None)
        _chat_requesting.discard(vid)
        
        # Restore original layout
        window = sublime.active_window()
        if window and window.id() in _original_layouts:
            layout = _original_layouts.pop(window.id())
            # Delay slightly to let Sublime finish closing the view
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
        
        # Get selected text
        selected_text = ""
        for region in view.sel():
            if not region.empty():
                selected_text += view.substr(region) + "\n"
        
        selected_text = selected_text.strip()
        if not selected_text:
            sublime.status_message("CodeContinue: No text selected")
            return
        
        # Get file info
        file_name = view.file_name() or "untitled"
        syntax = view.settings().get("syntax", "")
        lang = syntax.split("/")[-1].replace(".sublime-syntax", "").lower() if syntax else "unknown"
        base_name = file_name.split("\\")[-1].split("/")[-1]
        
        # Save and set layout
        wid = window.id()
        _original_layouts[wid] = window.get_layout()
        
        window.set_layout({
            "cols": [0.0, 0.6, 1.0],
            "rows": [0.0, 1.0],
            "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]
        })
        
        # Keep source in group 0
        window.set_view_index(view, 0, 0)
        
        # Create chat view in group 1
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
        
        # Register chat view
        cvid = chat_view.id()
        _chat_view_ids.add(cvid)
        
        # Build initial history
        initial_msg = (
            "Here is the selected code from `{0}` ({1}):\n\n"
            "```\n{2}\n```\n\n"
            "I'd like to discuss this code."
        ).format(base_name, lang, selected_text)
        
        session = {
            "history": [
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {"role": "user", "content": initial_msg}
            ],
            "endpoint": settings.get("endpoint", ""),
            "model": settings.get("model", ""),
            "timeout_s": settings.get("timeout_ms", 30000) / 1000.0,
            "headers": _build_api_headers(settings),
            "code": selected_text,
            "lang": lang,
        }
        _chat_sessions[cvid] = session
        
        # Write header
        header = (
            "═══ CodeContinue Chat ═══\n"
            "File: {0}  |  Language: {1}\n\n"
            "─── Selected Code ───\n"
            "{2}\n"
        ).format(base_name, lang, selected_text)
        
        chat_view.run_command("append", {"characters": header})
        chat_view.set_read_only(True)
        
        # Show thinking and send first request
        _chat_view_append(chat_view, "\n⏳ Thinking...\n")
        _chat_requesting.add(cvid)
        _chat_do_api_call(chat_view, session)
    
    def is_enabled(self):
        """Only enable when there is a non-empty selection."""
        for region in self.view.sel():
            if not region.empty():
                return True
        return False
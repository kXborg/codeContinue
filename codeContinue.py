import sublime
import sublime_plugin
import threading
import json
import urllib.request
import urllib.error
import time
import re

# Simple logger with timestamp to stdout
def _log(msg):
    ts = time.strftime('%H:%M:%S')
    print("CodeContinue [{0}] {1}".format(ts, msg))


def clean_markdown_fences(text):
    """
    Remove markdown code fence markers from LLM output.
    Handles patterns like:
    - ```python\ncode\n```
    - ```\ncode\n```
    - code```  (trailing fence)
    
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
    
    # Strip any remaining leading/trailing whitespace
    text = text.strip()
    
    return text


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

        # Insert <CURSOR_HERE> marker at cursor position relative to context start
        cursor_offset = cursor - start_point
        code_before = code[:cursor_offset]
        code_after = code[cursor_offset:]
        prompt = "Continue the following code. Output ONLY the code continuation, no markdown, no backticks, no <CURSOR_HERE>, no comments, no explanations:\n{0}<CURSOR_HERE>{1}".format(code_before, code_after)

        # Generate unique request ID for this view/cursor
        vid = view.id()
        request_id = (vid, cursor, time.time())
        pending_requests[vid] = request_id
        
        sublime.status_message("CodeContinue: Fetching suggestion...")
        
        # Async API call
        def fetch_completion():
            try:
                # Check if this request is still relevant
                if pending_requests.get(vid) != request_id:
                    return
                
                data = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a code completion expert. Output ONLY the code continuation without any markdown formatting, backticks, explanations, or comments. Do NOT include the <CURSOR_HERE> marker in your response."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 128,  # Increased from 10 to 128 tokens for better continuations
                    "stop": ["\n\n", "\n#", "\n//", "<CURSOR_HERE>"],  # Stop at boundaries
                    "temperature": 0.0  # Deterministic output
                }
                _log("Sending request to endpoint {0}".format(endpoint))
                req = urllib.request.Request(endpoint, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=timeout_ms) as response:
                    result = json.loads(response.read().decode())
                    completion = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    
                    # Clean markdown code fences (once per response, before processing)
                    completion = clean_markdown_fences(completion)
                    
                    # Verify request is still relevant after network call
                    if pending_requests.get(vid) == request_id and completion:
                        # Show phantom
                        sublime.set_timeout(lambda: show_phantom(view, cursor, completion), 0)
                    elif pending_requests.get(vid) == request_id:
                        sublime.status_message("CodeContinue: Empty response")
            except urllib.error.URLError as e:
                if pending_requests.get(vid) == request_id:
                    sublime.status_message("CodeContinue: Network error - {0}".format(str(e)[:50]))
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                if pending_requests.get(vid) == request_id:
                    sublime.status_message("CodeContinue: Parse error - {0}".format(str(e)[:50]))
            except Exception as e:
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

            # Compute indentation of the current line where insertion happens
            line_region = view.line(insert_pos)
            line_text = view.substr(line_region)
            import re
            m = re.match(r"^[ \t]*", line_text)
            current_indent = m.group(0) if m else ""

            # Prepare line to insert (first line)
            first_line = remaining.pop(0)

            # Remaining lines are already normalized (common indent stripped) by show_phantom
            rem_lines = remaining

            # Insert first line at the cursor (indent already exists in buffer)
            text_to_insert = first_line
            # If there are more lines, append a newline and apply indentation for the next line
            if rem_lines:
                text_to_insert += "\n" + current_indent

            view.insert(edit, insert_pos, text_to_insert)

            # Move cursor to end of inserted text (now at start of next line with indent when rem_lines exist)
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
import sublime
import sublime_plugin
import threading
import json
import urllib.request
import urllib.error
import time

# Global dict to store phantoms per view
phantoms = {}
# Cache for last context to reuse
last_context = {}


class CodeContinueListener(sublime_plugin.EventListener):
    def on_modified(self, view):
        settings = sublime.load_settings("CodeContinue.sublime-settings")
        trigger_langs = settings.get("trigger_language", [])
        if view.syntax().name.lower() not in [lang.lower() for lang in trigger_langs]:
            return
        
        # Heuristic triggering: Only on pauses after specific characters
        sel = view.sel()
        if len(sel) != 1:
            return
        cursor = sel[0].begin()
        if cursor == 0:
            return
        # Check last character
        last_char = view.substr(cursor - 1)
        if last_char in ['\n', ':', '(', '[', '{', '=', ' ', '\t'] or last_char.isalpha() and view.substr(cursor - 3).endswith('def '):
            # Debounce: 1s delay
            sublime.set_timeout(lambda: self._auto_suggest(view), 1000)

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

        # Get context: lines before and after cursor
        region = view.line(cursor)
        start_line = max(0, region.begin() - max_lines // 2)
        end_line = min(view.size(), region.end() + max_lines // 2)
        context_region = sublime.Region(start_line, end_line)
        code = view.substr(context_region)

        # Insert <cursor> marker
        cursor_offset = cursor - start_line
        code_before = code[:cursor_offset]
        code_after = code[cursor_offset:]
        prompt = "Continue the following code without any explanations or comments:\n{0}<cursor>{1}".format(code_before, code_after)

        # Async API call
        def fetch_completion():
            try:
                data = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a code completion assistant. Only output the code continuation, no explanations, comments, or extra text."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 10,  # Limit to 10 tokens for continuation
                    "stop": ["\n\n", "\n#", "\n//"],  # Stop early
                    "temperature": 0.1
                }
                req = urllib.request.Request(endpoint, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=timeout_ms) as response:
                    result = json.loads(response.read().decode())
                    completion = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if completion:
                        # Show phantom
                        sublime.set_timeout(lambda: show_phantom(view, cursor, completion), 0)
            except (urllib.error.URLError, ValueError, KeyError) as e:
                sublime.status_message("CodeContinue: API error - {0}".format(str(e)))

        threading.Thread(target=fetch_completion).start()


class CodeContinueAcceptCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        if view.id() not in phantoms:
            return
        phantom_set, suggestion = phantoms[view.id()]
        # Insert suggestion at cursor
        sel = view.sel()
        if len(sel) == 1:
            view.insert(edit, sel[0].begin(), suggestion)
        clear_phantoms(view)

def show_phantom(view, cursor, suggestion):
    global phantoms
    clear_phantoms(view)
    phantom_set = sublime.PhantomSet(view)
    # Create phantom at cursor position
    phantom = sublime.Phantom(sublime.Region(cursor, cursor), '<span style="color: gray">{0}</span>'.format(suggestion), sublime.LAYOUT_INLINE)
    phantom_set.update([phantom])
    phantoms[view.id()] = (phantom_set, suggestion)
    view.set_status('code_continue_visible', 'true')

def clear_phantoms(view):
    global phantoms
    if view.id() in phantoms:
        phantoms[view.id()][0].update([])
        del phantoms[view.id()]
    view.erase_status('code_continue_visible')
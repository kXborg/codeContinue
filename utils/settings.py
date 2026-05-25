"""Settings discovery, first-run setup, and the Configure command."""

import sublime
import sublime_plugin

from .log import _log


# Module-level globals used across the first-run setup dialog callbacks.
_setup_endpoint = None
_setup_model = None


def is_endpoint_configured(settings):
    """Return True when the configured endpoint looks like a real URL.

    `settings` is duck-typed: anything exposing `.get(key, default)` works.
    """
    endpoint = settings.get("endpoint", "").strip()
    if not endpoint or "your-api" in endpoint.lower():
        return False
    return True


def show_endpoint_config_panel(view):
    """Show input panel chain to configure endpoint + model on demand."""
    # Capture a stable window reference (the view's window can be None by the
    # time the chained callback fires).
    window = (view.window() if view else None) or sublime.active_window()
    if not window:
        sublime.status_message("CodeContinue: No active window for configuration.")
        return

    settings = sublime.load_settings("CodeContinue.sublime-settings")
    current_endpoint = settings.get("endpoint", "https://your-api.com/v1/chat/completions")

    def on_endpoint_done(endpoint_text):
        if endpoint_text.strip():
            settings.set("endpoint", endpoint_text.strip())

            current_model = settings.get("model", "gpt-3.5-turbo")

            def on_model_done(model_text):
                if model_text.strip():
                    settings.set("model", model_text.strip())
                    sublime.save_settings("CodeContinue.sublime-settings")
                    sublime.status_message("CodeContinue: Configuration saved! Ready to use.")
                    _log("Configuration saved: endpoint and model set")

            window.show_input_panel(
                "CodeContinue - Model name:",
                current_model,
                on_model_done,
                None,
                None
            )
        else:
            sublime.status_message("CodeContinue: Endpoint not configured. Run 'CodeContinue: Configure' to set it up.")

    window.show_input_panel(
        "CodeContinue - API Endpoint URL:",
        current_endpoint,
        on_endpoint_done,
        None,
        None
    )


def plugin_loaded():
    """Sublime calls this hook when the plugin is loaded."""
    settings = sublime.load_settings("CodeContinue.sublime-settings")

    endpoint = settings.get("endpoint", "").strip()
    model = settings.get("model", "").strip()

    if not endpoint or not model:
        _log("CodeContinue: First run detected, showing setup dialog")
        sublime.set_timeout(show_setup_dialog, 500)


def show_setup_dialog():
    """First-run setup: prompt for endpoint, then model, then optional API key."""
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
    """Prompt for an optional API key after the model is captured."""
    global _setup_model
    _setup_model = model
    window = sublime.active_window()
    if not window:
        return

    window.show_input_panel(
        "CodeContinue Setup: API key (optional, leave blank to skip)",
        "",
        on_api_key_entered,
        None,
        None
    )


def on_api_key_entered(api_key):
    """Final setup step: save endpoint, model, and (optional) API key."""
    global _setup_endpoint, _setup_model

    if not _setup_endpoint or not _setup_model:
        sublime.error_dialog("CodeContinue Setup Error: Endpoint or model not set")
        return

    settings = sublime.load_settings("CodeContinue.sublime-settings")
    settings.set("endpoint", _setup_endpoint)
    settings.set("model", _setup_model)
    settings.set("api_key", api_key.strip() if api_key else "")
    sublime.save_settings("CodeContinue.sublime-settings")

    _log("CodeContinue: Configuration saved. Endpoint: {0}, Model: {1}, API key set: {2}".format(
        _setup_endpoint, _setup_model, bool(api_key.strip()) if api_key else False
    ))
    sublime.message_dialog(
        "CodeContinue configured successfully!\n\nEndpoint: {0}\nModel: {1}\n\nPress Ctrl+Enter to get a code suggestion.".format(
            _setup_endpoint, _setup_model
        )
    )


class CodeContinueConfigureCommand(sublime_plugin.TextCommand):
    """Reconfigure endpoint, model, and API key from the command palette."""
    def run(self, edit):
        # self.view.window() can return None inside the chained callbacks (e.g.
        # when the command was invoked from the command palette), so fall back
        # to active_window and capture once.
        window = self.view.window() or sublime.active_window()
        if not window:
            sublime.error_dialog("CodeContinue: No active window to configure in.")
            return

        settings = sublime.load_settings("CodeContinue.sublime-settings")

        current_endpoint = settings.get("endpoint", "https://your-api.com/v1/chat/completions")

        def on_endpoint_done(endpoint_text):
            if endpoint_text.strip():
                settings.set("endpoint", endpoint_text.strip())

                current_model = settings.get("model", "gpt-3.5-turbo")

                def on_model_done(model_text):
                    if model_text.strip():
                        settings.set("model", model_text.strip())

                        current_api_key = settings.get("api_key", "")

                        def on_api_key_done(api_key_text):
                            settings.set("api_key", api_key_text.strip() if api_key_text.strip() else "")
                            sublime.save_settings("CodeContinue.sublime-settings")
                            sublime.status_message("CodeContinue: Configuration saved!")
                            _log("Configuration updated via Command Palette")

                        window.show_input_panel(
                            "CodeContinue - API Key (optional, leave blank to skip):",
                            current_api_key,
                            on_api_key_done,
                            None,
                            None
                        )

                window.show_input_panel(
                    "CodeContinue - Model name:",
                    current_model,
                    on_model_done,
                    None,
                    None
                )

        window.show_input_panel(
            "CodeContinue - API Endpoint URL:",
            current_endpoint,
            on_endpoint_done,
            None,
            None
        )

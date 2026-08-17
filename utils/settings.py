"""Settings discovery, first-run setup, and the Configure command."""

import threading
import sublime
import sublime_plugin

from .api import normalize_endpoint, fetch_models, test_endpoint_connectivity
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


def _save_settings():
    """Persist CodeContinue settings to disk."""
    sublime.save_settings("CodeContinue.sublime-settings")


def _prompt_for_model(window, settings, default_model, on_done, on_cancel):
    """Fetch available models in background and prompt via quick panel or input panel."""
    endpoint = settings.get("endpoint", "")
    api_key = settings.get("api_key", "")

    sublime.status_message("CodeContinue: Detecting available models...")

    def fetch_worker():
        is_ok, msg = test_endpoint_connectivity(endpoint, api_key)
        models = fetch_models(endpoint, api_key) if is_ok else []

        def show_ui():
            if not window:
                return

            if not is_ok:
                sublime.status_message("CodeContinue: ⚠ {0}".format(msg))
                _log("Endpoint connectivity: {0}".format(msg))
            else:
                _log("Endpoint connectivity: OK ({0} models found)".format(len(models)))

            if models:
                options = list(models)
                options.append("✎ Enter model name manually...")

                def on_quick_select(idx):
                    if idx < 0:
                        on_cancel()
                    elif idx < len(models):
                        on_done(models[idx])
                    else:
                        window.show_input_panel(
                            "CodeContinue - Enter Model Name:",
                            default_model,
                            on_done,
                            None,
                            on_cancel,
                        )

                window.show_quick_panel(options, on_quick_select)
            else:
                window.show_input_panel(
                    "CodeContinue - Enter Model Name:",
                    default_model,
                    on_done,
                    None,
                    on_cancel,
                )

        sublime.set_timeout(show_ui, 0)

    threading.Thread(target=fetch_worker, daemon=True).start()


def show_endpoint_config_panel(view):
    """Show input panel chain to configure endpoint + model on demand.

    Saves incrementally: each value is persisted as soon as it is captured,
    so pressing Escape on a later panel preserves earlier entries.
    """
    window = (view.window() if view else None) or sublime.active_window()
    if not window:
        sublime.status_message("CodeContinue: No active window for configuration.")
        return

    settings = sublime.load_settings("CodeContinue.sublime-settings")
    current_endpoint = settings.get("endpoint", "http://localhost:1234")

    def on_endpoint_done(endpoint_text):
        norm_endpoint = normalize_endpoint(endpoint_text)
        if norm_endpoint:
            settings.set("endpoint", norm_endpoint)
            _save_settings()
            _log("Configuration: endpoint saved ({0})".format(norm_endpoint))

            current_model = settings.get("model", "gpt-3.5-turbo")

            def on_model_done(model_text):
                if model_text.strip():
                    settings.set("model", model_text.strip())
                    _save_settings()
                    sublime.status_message("CodeContinue: Configuration saved! Ready to use.")
                    _log("Configuration saved: endpoint and model set")

            def on_model_cancel():
                sublime.status_message("CodeContinue: Setup cancelled. Endpoint was saved.")
                _log("Configuration: model panel cancelled; endpoint preserved")

            _prompt_for_model(window, settings, current_model, on_model_done, on_model_cancel)
        else:
            sublime.status_message("CodeContinue: Endpoint not configured. Run 'CodeContinue: Configure' to set it up.")

    def on_endpoint_cancel():
        sublime.status_message("CodeContinue: Setup cancelled.")
        _log("Configuration: endpoint panel cancelled")

    window.show_input_panel(
        "CodeContinue - API Endpoint (e.g. http://localhost:1234):",
        current_endpoint,
        on_endpoint_done,
        None,
        on_endpoint_cancel,
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
    """First-run setup: prompt for endpoint, then model, then optional API key.

    Saves incrementally so that pressing Escape at any panel preserves
    whatever has been entered so far.
    """
    global _setup_endpoint, _setup_model
    _setup_endpoint = None
    _setup_model = None

    window = sublime.active_window()
    if not window:
        return

    window.show_input_panel(
        "CodeContinue Setup: API Endpoint URL (e.g. http://localhost:1234 or full URL):",
        "https://api.openai.com/v1/chat/completions",
        on_endpoint_entered,
        None,
        _on_setup_cancel_endpoint,
    )


def _on_setup_cancel_endpoint():
    """Escape pressed on the endpoint panel — nothing was entered yet."""
    sublime.status_message("CodeContinue: Setup cancelled.")
    _log("Setup: endpoint panel cancelled")


def on_endpoint_entered(endpoint):
    global _setup_endpoint
    norm_endpoint = normalize_endpoint(endpoint)
    _setup_endpoint = norm_endpoint

    settings = sublime.load_settings("CodeContinue.sublime-settings")
    settings.set("endpoint", norm_endpoint)
    _save_settings()
    _log("Setup: endpoint saved incrementally ({0})".format(norm_endpoint))

    window = sublime.active_window()
    if not window:
        return

    _prompt_for_model(window, settings, "gpt-3.5-turbo", on_model_entered, _on_setup_cancel_model)


def _on_setup_cancel_model():
    """Escape pressed on the model panel — endpoint was already saved."""
    sublime.status_message("CodeContinue: Setup cancelled. Endpoint was saved.")
    _log("Setup: model panel cancelled; endpoint preserved")


def on_model_entered(model):
    """Prompt for an optional API key after the model is captured."""
    global _setup_model
    _setup_model = model

    settings = sublime.load_settings("CodeContinue.sublime-settings")
    settings.set("model", model)
    _save_settings()
    _log("Setup: model saved incrementally")

    window = sublime.active_window()
    if not window:
        return

    window.show_input_panel(
        "CodeContinue Setup: API key (optional, leave blank to skip):",
        "",
        on_api_key_entered,
        None,
        _on_setup_cancel_api_key,
    )


def _on_setup_cancel_api_key():
    """Escape pressed on the API key panel — endpoint and model already saved."""
    sublime.status_message("CodeContinue: Setup cancelled. Endpoint and model were saved.")
    _log("Setup: API key panel cancelled; endpoint and model preserved")


def on_api_key_entered(api_key):
    """Prompt for optional system prompt after API key is captured."""
    global _setup_endpoint, _setup_model

    settings = sublime.load_settings("CodeContinue.sublime-settings")
    settings.set("api_key", api_key.strip() if api_key else "")
    _save_settings()

    window = sublime.active_window()
    if not window:
        _finish_setup(settings)
        return

    current_prompt = settings.get("system_prompt", "")

    window.show_input_panel(
        "CodeContinue Setup: Custom system prompt (optional, leave blank for default):",
        current_prompt,
        on_system_prompt_entered,
        None,
        _on_setup_cancel_system_prompt,
    )


def _on_setup_cancel_system_prompt():
    """Escape on system prompt panel — all earlier values already saved."""
    settings = sublime.load_settings("CodeContinue.sublime-settings")
    sublime.status_message("CodeContinue: Setup cancelled. Previous settings were saved.")
    _log("Setup: system prompt panel cancelled; earlier settings preserved")
    _finish_setup(settings)


def on_system_prompt_entered(prompt_text):
    """Final setup step: save system prompt."""
    global _setup_endpoint, _setup_model

    settings = sublime.load_settings("CodeContinue.sublime-settings")
    settings.set("system_prompt", prompt_text.strip())
    _save_settings()
    _log("Setup: system prompt saved")
    _finish_setup(settings)


def _finish_setup(settings):
    """Show the completion dialog and clear setup globals."""
    global _setup_endpoint, _setup_model

    endpoint = settings.get("endpoint", "")
    model = settings.get("model", "")

    _log("CodeContinue: Configuration saved. Endpoint: {0}, Model: {1}".format(endpoint, model))
    sublime.message_dialog(
        "CodeContinue configured successfully!\n\nEndpoint: {0}\nModel: {1}\n\nPress Tab to accept suggestions once keybindings are configured.".format(
            endpoint, model
        )
    )

    _setup_endpoint = None
    _setup_model = None


class CodeContinueConfigureCommand(sublime_plugin.TextCommand):
    """Reconfigure endpoint, model, and API key from the command palette.

    Saves incrementally: each value is persisted as soon as the user confirms
    it, so pressing Escape on a later panel preserves earlier changes.
    """
    def run(self, edit):
        window = self.view.window() or sublime.active_window()
        if not window:
            sublime.error_dialog("CodeContinue: No active window to configure in.")
            return

        settings = sublime.load_settings("CodeContinue.sublime-settings")
        current_endpoint = settings.get("endpoint", "http://localhost:1234")

        def on_endpoint_done(endpoint_text):
            norm_endpoint = normalize_endpoint(endpoint_text)
            if norm_endpoint:
                settings.set("endpoint", norm_endpoint)
                _save_settings()
                _log("Configure: endpoint saved incrementally ({0})".format(norm_endpoint))

                current_model = settings.get("model", "gpt-3.5-turbo")

                def on_model_done(model_text):
                    if model_text.strip():
                        settings.set("model", model_text.strip())
                        _save_settings()
                        _log("Configure: model saved incrementally")

                        current_api_key = settings.get("api_key", "")

                        def on_api_key_done(api_key_text):
                            settings.set("api_key", api_key_text.strip() if api_key_text.strip() else "")
                            _save_settings()
                            _log("Configure: API key saved incrementally")

                            current_prompt = settings.get("system_prompt", "")

                            def on_prompt_done(prompt_text):
                                settings.set("system_prompt", prompt_text.strip())
                                _save_settings()
                                sublime.status_message("CodeContinue: Configuration saved!")
                                _log("Configuration updated via Command Palette")

                            def on_prompt_cancel():
                                sublime.status_message("CodeContinue: System prompt unchanged. All other settings were saved.")
                                _log("Configure: system prompt panel cancelled; earlier settings preserved")

                            window.show_input_panel(
                                "CodeContinue - System prompt (optional, blank = built-in default):",
                                current_prompt,
                                on_prompt_done,
                                None,
                                on_prompt_cancel,
                            )

                        def on_api_key_cancel():
                            sublime.status_message("CodeContinue: API key unchanged. Endpoint and model were saved.")
                            _log("Configure: API key panel cancelled; endpoint and model preserved")

                        window.show_input_panel(
                            "CodeContinue - API Key (optional, leave blank to skip):",
                            current_api_key,
                            on_api_key_done,
                            None,
                            on_api_key_cancel,
                        )

                def on_model_cancel():
                    sublime.status_message("CodeContinue: Model unchanged. Endpoint was saved.")
                    _log("Configure: model panel cancelled; endpoint preserved")

                _prompt_for_model(window, settings, current_model, on_model_done, on_model_cancel)

        def on_endpoint_cancel():
            sublime.status_message("CodeContinue: Configuration cancelled.")
            _log("Configure: endpoint panel cancelled")

        window.show_input_panel(
            "CodeContinue - API Endpoint URL (e.g. http://localhost:1234 or full URL):",
            current_endpoint,
            on_endpoint_done,
            None,
            on_endpoint_cancel,
        )


"""Settings discovery, first-run setup, and the Configure command."""

import os
import json
import re
import threading
# pyrefly: ignore[missing-import]
import sublime
import sublime_plugin

from .api import normalize_endpoint, fetch_models, test_endpoint_connectivity
from .log import _log


DEFAULT_ENDPOINT = "http://localhost:8000/v1/chat/completions"

# Module-level globals used across the first-run setup dialog callbacks.
_setup_endpoint = None
_setup_model = None


def get_default_or_configured_endpoint(settings):
    """Return configured endpoint or DEFAULT_ENDPOINT if empty/placeholder."""
    if not settings:
        return DEFAULT_ENDPOINT
    endpoint = settings.get("endpoint", "").strip()
    if not endpoint or "your-api" in endpoint.lower() or "trycloudflare.com" in endpoint.lower():
        return DEFAULT_ENDPOINT
    return endpoint


def is_endpoint_configured(settings):
    """Return True when the configured endpoint looks like a real URL.

    `settings` is duck-typed: anything exposing `.get(key, default)` works.
    """
    endpoint = settings.get("endpoint", "").strip()
    if not endpoint or "your-api" in endpoint.lower() or "trycloudflare.com" in endpoint.lower():
        return False
    return True


class FeatureSettings:
    """Settings adapter providing feature-specific overrides with global fallbacks.

    Example:
        For feature_prefix="chat", calling cfg.get("model") will first check
        "chat_model". If not set or empty, it falls back to "model".
    """

    def __init__(self, settings, feature_prefix=""):
        self._settings = settings
        self._prefix = feature_prefix.strip("_") if feature_prefix else ""

    def get(self, key, default=None):
        if not self._settings:
            return default
        if self._prefix:
            specific_key = "{0}_{1}".format(self._prefix, key)
            val = self._settings.get(specific_key)
            if val is not None and val != "":
                return val
        return self._settings.get(key, default)


def get_feature_settings(settings, feature_prefix=""):
    """Return a FeatureSettings adapter for the given feature prefix."""
    return FeatureSettings(settings, feature_prefix)


def _save_settings():
    """Persist CodeContinue settings to disk."""
    sublime.save_settings("CodeContinue.sublime-settings")


def update_status_bar(view, state_text=None):
    """Update Sublime Text status bar with current CodeContinue model/state."""
    if not view or not getattr(view, "is_valid", lambda: True)():
        return
    if getattr(view, "is_scratch", lambda: False)():
        return

    settings = sublime.load_settings("CodeContinue.sublime-settings")
    if not settings.get("status_bar", True):
        if hasattr(view, "erase_status"):
            view.erase_status("code_continue_status")
        return

    model = settings.get("model", "")
    if not model:
        status = "CodeContinue: [No Model]"
    elif state_text:
        status = "CodeContinue: [{0}] {1}".format(model, state_text)
    else:
        status = "CodeContinue: [{0}]".format(model)

    if hasattr(view, "set_status"):
        view.set_status("code_continue_status", status)


def _refresh_all_status_bars():
    """Refresh status bar across all views in all open windows."""
    if not hasattr(sublime, "windows"):
        return
    for window in sublime.windows():
        for view in window.views():
            update_status_bar(view)


def get_user_keymap_path(packages_path=None):
    """Return absolute path to User Default (Platform).sublime-keymap."""
    if not packages_path:
        packages_path = getattr(sublime, "packages_path", lambda: "")()
    if not packages_path:
        return None
    user_dir = os.path.join(packages_path, "User")
    platform_name = getattr(sublime, "platform", lambda: "windows")()
    platform_map = {
        "windows": "Default (Windows).sublime-keymap",
        "osx": "Default (OSX).sublime-keymap",
        "linux": "Default (Linux).sublime-keymap",
    }
    keymap_name = platform_map.get(platform_name, "Default.sublime-keymap")
    return os.path.join(user_dir, keymap_name)


def get_keybinding_preset(preset="recommended"):
    """Return keybinding list for the specified preset."""
    if preset == "single_key":
        return [
            {
                "keys": ["ctrl+enter"],
                "command": "code_continue_accept",
                "context": [
                    {"key": "code_continue_visible", "operator": "equal", "operand": True}
                ]
            },
            {
                "keys": ["ctrl+enter"],
                "command": "code_continue_suggest"
            },
            {
                "keys": ["escape"],
                "command": "code_continue_dismiss",
                "context": [
                    {"key": "code_continue_visible", "operator": "equal", "operand": True}
                ]
            }
        ]
    # Default: "recommended"
    return [
        {
            "keys": ["tab"],
            "command": "code_continue_accept",
            "context": [
                {"key": "code_continue_visible", "operator": "equal", "operand": True}
            ]
        },
        {
            "keys": ["ctrl+enter"],
            "command": "code_continue_suggest"
        },
        {
            "keys": ["escape"],
            "command": "code_continue_dismiss",
            "context": [
                {"key": "code_continue_visible", "operator": "equal", "operand": True}
            ]
        }
    ]


def install_user_keybindings(preset="recommended", packages_path=None):
    """Write or update CodeContinue keybindings in the user's keymap file."""
    keymap_path = get_user_keymap_path(packages_path)
    if not keymap_path:
        return False, "Could not determine User packages path."

    user_dir = os.path.dirname(keymap_path)
    if not os.path.exists(user_dir):
        try:
            os.makedirs(user_dir)
        except Exception as e:
            return False, "Failed to create User directory: {0}".format(e)

    existing = []
    if os.path.exists(keymap_path):
        try:
            with open(keymap_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                clean = re.sub(r"//.*", "", content)
                clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.DOTALL)
                parsed = json.loads(clean)
                if isinstance(parsed, list):
                    existing = [
                        b for b in parsed
                        if not (isinstance(b, dict) and b.get("command") in (
                            "code_continue_accept",
                            "code_continue_suggest",
                            "code_continue_dismiss"
                        ))
                    ]
        except Exception:
            existing = []

    new_bindings = get_keybinding_preset(preset)
    existing.extend(new_bindings)

    try:
        with open(keymap_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=4)
        return True, "Keybindings installed in User/{0}".format(os.path.basename(keymap_path))
    except Exception as e:
        return False, "Failed to write keymap file: {0}".format(e)


def _prompt_for_model(window, target, default_model="gpt-3.5-turbo", on_done=None, on_cancel=None, title="CodeContinue - Enter Model Name:", api_key=None):
    """Fetch available models in background and prompt via quick panel or input panel."""
    if isinstance(target, str):
        endpoint = target
    elif hasattr(target, "get"):
        endpoint = target.get("endpoint", "")
        if api_key is None:
            api_key = target.get("api_key", "")
    else:
        endpoint = ""
    api_key = api_key or ""

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
                        if on_cancel:
                            on_cancel()
                    elif idx < len(models):
                        if on_done:
                            on_done(models[idx])
                    else:
                        window.show_input_panel(
                            title,
                            default_model,
                            on_done,
                            None,
                            on_cancel,
                        )

                window.show_quick_panel(options, on_quick_select)
            else:
                window.show_input_panel(
                    title,
                    default_model,
                    on_done,
                    None,
                    on_cancel,
                )

        sublime.set_timeout(show_ui, 0)

    threading.Thread(target=fetch_worker, daemon=True).start()


def plugin_loaded():
    """Sublime calls this hook when the plugin is loaded."""
    settings = sublime.load_settings("CodeContinue.sublime-settings")

    endpoint = settings.get("endpoint", "").strip()
    model = settings.get("model", "").strip()

    if not endpoint or not model:
        _log("CodeContinue: First run detected, showing setup dialog")
        sublime.set_timeout(show_setup_dialog, 500)

    if hasattr(settings, "add_on_change"):
        settings.add_on_change("code_continue_status_bar", lambda: _refresh_all_status_bars())

    sublime.set_timeout(_refresh_all_status_bars, 200)


def run_configuration_wizard(window=None, on_complete=None):
    """Step-by-step configuration wizard covering Completion, Chat, and Keybindings."""
    if not window:
        window = sublime.active_window()
    if not window:
        return

    settings = sublime.load_settings("CodeContinue.sublime-settings")
    current_endpoint = get_default_or_configured_endpoint(settings)

    state = {
        "endpoint": current_endpoint,
        "model": settings.get("model", "") or "gpt-3.5-turbo",
        "api_key": settings.get("api_key", ""),
        "system_prompt": settings.get("system_prompt", ""),
        "chat_endpoint": settings.get("chat_endpoint", ""),
        "chat_model": settings.get("chat_model", ""),
        "chat_api_key": settings.get("chat_api_key", ""),
        "keybindings": "Not configured",
    }

    # Step 1: Completion Endpoint
    def step1_endpoint():
        def on_done(text):
            norm = normalize_endpoint(text) or DEFAULT_ENDPOINT
            state["endpoint"] = norm
            settings.set("endpoint", norm)
            _save_settings()
            _log("Wizard Step 1: Completion Endpoint saved ({0})".format(norm))
            sublime.set_timeout(step2_model, 50)

        def on_cancel():
            sublime.status_message("CodeContinue: Setup cancelled.")
            _log("Wizard cancelled at Step 1")

        window.show_input_panel(
            "CodeContinue Setup (1/8) - Completion API Endpoint URL:",
            state["endpoint"],
            on_done,
            None,
            on_cancel,
        )

    # Step 2: Completion Model
    def step2_model():
        def on_done(model_name):
            model_name = (model_name or "").strip() or "gpt-3.5-turbo"
            state["model"] = model_name
            settings.set("model", model_name)
            _save_settings()
            _refresh_all_status_bars()
            _log("Wizard Step 2: Completion Model saved ({0})".format(model_name))
            sublime.set_timeout(step3_api_key, 50)

        def on_cancel():
            sublime.status_message("CodeContinue: Setup cancelled. Endpoint was saved.")
            _log("Wizard cancelled at Step 2")

        _prompt_for_model(
            window,
            target=state["endpoint"],
            default_model=state["model"],
            on_done=on_done,
            on_cancel=on_cancel,
            title="CodeContinue Setup (2/8) - Enter Completion Model Name:",
            api_key=state["api_key"],
        )

    # Step 3: Completion API Key
    def step3_api_key():
        def on_done(text):
            api_key = text.strip()
            state["api_key"] = api_key
            settings.set("api_key", api_key)
            _save_settings()
            _log("Wizard Step 3: Completion API Key saved")
            sublime.set_timeout(step4_system_prompt, 50)

        def on_cancel():
            sublime.status_message("CodeContinue: Setup cancelled. Previous settings were saved.")
            _log("Wizard cancelled at Step 3")

        window.show_input_panel(
            "CodeContinue Setup (3/8) - Completion API Key (optional, press Enter to skip):",
            state["api_key"],
            on_done,
            None,
            on_cancel,
        )

    # Step 4: System Prompt
    def step4_system_prompt():
        def on_done(text):
            prompt_text = text.strip()
            state["system_prompt"] = prompt_text
            settings.set("system_prompt", prompt_text)
            _save_settings()
            _log("Wizard Step 4: System Prompt saved")
            sublime.set_timeout(step5_chat_endpoint, 50)

        def on_cancel():
            sublime.status_message("CodeContinue: Setup cancelled. Previous settings were saved.")
            _log("Wizard cancelled at Step 4")

        window.show_input_panel(
            "CodeContinue Setup (4/8) - Completion System Prompt (optional, press Enter for default):",
            state["system_prompt"],
            on_done,
            None,
            on_cancel,
        )

    # Step 5: Chat Endpoint
    def step5_chat_endpoint():
        default_chat_ep = state["chat_endpoint"] or state["endpoint"]

        def on_done(text):
            text = text.strip()
            norm = normalize_endpoint(text) if text else state["endpoint"]
            state["chat_endpoint"] = norm
            settings.set("chat_endpoint", norm)
            _save_settings()
            _log("Wizard Step 5: Chat Endpoint saved ({0})".format(norm))
            sublime.set_timeout(step6_chat_model, 50)

        def on_cancel():
            sublime.status_message("CodeContinue: Setup cancelled. Previous settings were saved.")
            _log("Wizard cancelled at Step 5")

        window.show_input_panel(
            "CodeContinue Setup (5/8) - Chat Endpoint URL (press Enter to use {0}):".format(state["endpoint"]),
            default_chat_ep,
            on_done,
            None,
            on_cancel,
        )

    # Step 6: Chat Model
    def step6_chat_model():
        default_chat_model = state["chat_model"] or state["model"]

        def on_done(model_name):
            model_name = (model_name or "").strip() or state["model"]
            state["chat_model"] = model_name
            settings.set("chat_model", model_name)
            _save_settings()
            _log("Wizard Step 6: Chat Model saved ({0})".format(model_name))
            sublime.set_timeout(step7_chat_api_key, 50)

        def on_cancel():
            sublime.status_message("CodeContinue: Setup cancelled. Previous settings were saved.")
            _log("Wizard cancelled at Step 6")

        _prompt_for_model(
            window,
            target=state["chat_endpoint"],
            default_model=default_chat_model,
            on_done=on_done,
            on_cancel=on_cancel,
            title="CodeContinue Setup (6/8) - Enter Chat Model Name:",
            api_key=state["chat_api_key"] or state["api_key"],
        )

    # Step 7: Chat API Key
    def step7_chat_api_key():
        def on_done(text):
            chat_key = text.strip()
            state["chat_api_key"] = chat_key
            settings.set("chat_api_key", chat_key)
            _save_settings()
            _log("Wizard Step 7: Chat API Key saved")
            sublime.set_timeout(step8_keybindings, 50)

        def on_cancel():
            sublime.status_message("CodeContinue: Setup cancelled. Previous settings were saved.")
            _log("Wizard cancelled at Step 7")

        window.show_input_panel(
            "CodeContinue Setup (7/8) - Chat API Key (optional, press Enter to reuse completion key):",
            state["chat_api_key"],
            on_done,
            None,
            on_cancel,
        )

    # Step 8: Keybindings Quick Panel
    def step8_keybindings():
        items = [
            [
                "✓ Install Recommended Keybindings (Default)",
                "Tab: Accept | Ctrl+Enter: Suggest | Escape: Dismiss",
            ],
            [
                "✓ Single-Key Setup",
                "Ctrl+Enter: Both Suggest and Accept | Escape: Dismiss",
            ],
            [
                "✗ Skip Keybinding Setup",
                "Keep existing keymap or configure manually later",
            ],
        ]

        def on_select(idx):
            if idx == 0:
                ok, msg = install_user_keybindings("recommended")
                state["keybindings"] = "Installed (Tab: Accept, Ctrl+Enter: Suggest, Esc: Dismiss)" if ok else "Failed: " + msg
            elif idx == 1:
                ok, msg = install_user_keybindings("single_key")
                state["keybindings"] = "Installed (Ctrl+Enter: Suggest & Accept, Esc: Dismiss)" if ok else "Failed: " + msg
            else:
                state["keybindings"] = "Skipped (Configure manually in Preferences > Key Bindings)"

            sublime.set_timeout(step9_finish, 50)

        window.show_quick_panel(items, on_select)

    # Step 9: Finish
    def step9_finish():
        _save_settings()
        _refresh_all_status_bars()

        summary = (
            "CodeContinue configured successfully!\n\n"
            "• Completion Engine:\n"
            "  Endpoint: {0}\n"
            "  Model:    {1}\n\n"
            "• Chat Engine:\n"
            "  Endpoint: {2}\n"
            "  Model:    {3}\n\n"
            "• Keybindings:\n"
            "  {4}\n\n"
            "Ready to code with intent!"
        ).format(
            state["endpoint"],
            state["model"],
            state["chat_endpoint"] or state["endpoint"],
            state["chat_model"] or state["model"],
            state["keybindings"],
        )

        sublime.message_dialog(summary)
        sublime.status_message("CodeContinue: Configuration saved! Ready to use.")
        _log("Wizard complete: {0}".format(summary.replace("\n", " ")))
        if on_complete:
            on_complete()

    # Launch step 1
    step1_endpoint()


def show_setup_dialog():
    """First-run setup: launch the configuration wizard."""
    window = sublime.active_window()
    if not window and hasattr(sublime, "windows"):
        windows = sublime.windows()
        if windows:
            window = windows[0]
    if window:
        run_configuration_wizard(window)
    else:
        # Retry shortly if Sublime window is still initializing on startup (common on macOS)
        sublime.set_timeout(show_setup_dialog, 1000)


def show_endpoint_config_panel(view):
    """Show configuration wizard on demand."""
    window = (view.window() if view else None) or sublime.active_window()
    run_configuration_wizard(window)


class CodeContinueConfigureCommand(sublime_plugin.WindowCommand):
    """Reconfigure CodeContinue via Command Palette or Menu."""
    def run(self):
        window = self.window or sublime.active_window()
        run_configuration_wizard(window)


class CodeContinueSwitchModelCommand(sublime_plugin.ApplicationCommand):
    """Quickly switch active model from detected models or manual input."""

    def run(self, feature=None):
        window = sublime.active_window()
        if not window:
            return

        raw_settings = sublime.load_settings("CodeContinue.sublime-settings")

        if not feature:
            global_model = raw_settings.get("model") or "Not set"
            chat_model = raw_settings.get("chat_model") or "Inherits global ({0})".format(global_model)
            edit_model = raw_settings.get("edit_model") or "Inherits global ({0})".format(global_model)

            items = [
                ["Global / Completion Model", "Current: {0}".format(global_model)],
                ["Chat Model Override", "Current: {0}".format(chat_model)],
                ["Edit Model Override", "Current: {0}".format(edit_model)],
            ]

            def on_feature_select(idx):
                if idx == 0:
                    self._switch_for_feature(window, raw_settings, "global")
                elif idx == 1:
                    self._switch_for_feature(window, raw_settings, "chat")
                elif idx == 2:
                    self._switch_for_feature(window, raw_settings, "edit")

            window.show_quick_panel(items, on_feature_select)
        else:
            self._switch_for_feature(window, raw_settings, feature)

    def _switch_for_feature(self, window, raw_settings, feature):
        feature_cfg = get_feature_settings(raw_settings, "" if feature == "global" else feature)
        current_model = feature_cfg.get("model", "")
        target_key = "model" if feature == "global" else "{0}_model".format(feature)
        feature_title = feature.capitalize() if feature != "global" else "Global"

        def on_done(selected_model):
            selected_model = (selected_model or "").strip()
            if selected_model:
                raw_settings.set(target_key, selected_model)
                _save_settings()
                sublime.status_message("CodeContinue: {0} model set to '{1}'".format(feature_title, selected_model))
                _refresh_all_status_bars()

        def on_cancel():
            sublime.status_message("CodeContinue: Model switch cancelled.")

        _prompt_for_model(window, feature_cfg, current_model, on_done, on_cancel)


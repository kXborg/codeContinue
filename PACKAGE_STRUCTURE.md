# Package Structure for codeContinue

This document explains the structure of the codeContinue plugin for Sublime Text.

## Directory Layout

```
codeContinue/
├── codeContinue.py                    # Main plugin entry point (registers commands/listeners)
├── CodeContinue.sublime-settings      # Default settings template (includes dual-engine & streaming options)
├── Context.sublime-menu               # Right-click context menu (Chat, Edit & 1-Click Presets)
├── Default.sublime-commands           # Command palette entries (Configure, Switch Model, Chat, Edit, Presets)
├── Default.sublime-keymap             # Default keybindings template (empty by default)
├── Main.sublime-menu                  # Preferences > Package Settings menu
├── messages.json                      # Package Control post-install & upgrade messaging map
├── messages/
│   ├── install.txt                    # Installation welcome guide & keybinding setup
│   ├── 2.4.0.txt                      # v2.4.0 release notes
│   ├── 2.5.0.txt                      # v2.5.0 release notes
│   └── 2.5.1.txt                      # v2.5.1 release notes
├── utils/
│   ├── __init__.py                    # Submodule marker
│   ├── api.py                         # OpenAI/Anthropic providers, SSE stream parser, model discovery
│   ├── chat.py                        # Split-pane real-time streaming Markdown chat & quick presets
│   ├── edit.py                        # In-place code rewrite with interactive diff review & presets
│   ├── log.py                         # Debug and error logging helpers
│   ├── settings.py                    # Dual-Engine adapter, status bar widget, model switcher, wizard
│   ├── suggest.py                     # FIM autocomplete, suffix trimming, status bar hooks, phantoms
│   └── text_utils.py                  # Diff computation, suffix overlap trimmer, fence cleaner
├── tests/                             # Unit test suite (runs in standard python unittest)
│   ├── test_api.py
│   ├── test_settings.py
│   ├── test_suggest.py
│   └── test_text_utils.py
├── tools/                             # Standalone dev/experiments installers
│   ├── README.md                      # Documentation for installers
│   ├── install.py                     # Interactive CLI installer
│   └── install_gui.py                 # Cross-platform Tkinter GUI installer
├── README.md                          # User documentation & configuration guide
└── LICENSE                            # License file
```

## How It Works with Package Control

1. **Installation**: User installs via Package Control (`Package Control: Install Package` >> `CodeContinue`).
2. **First Launch**: `plugin_loaded()` detects first run if endpoint or model is unconfigured.
3. **Setup Wizard**: Prompts for endpoint, auto-detects available models from `/v1/models` (or `/api/tags`), and prompts for optional API key.
4. **Configuration Saved**: Settings saved automatically to `Packages/User/CodeContinue.sublime-settings`.
5. **Welcome Message**: Package Control displays `messages/install.txt` explaining split-view keybinding setup.

## Module Descriptions

### codeContinue.py
- Minimal top-level entry point discovered by Sublime Text on startup.
- Imports commands, listeners, and `plugin_loaded` from `utils/` into the package namespace.

### utils/settings.py
- Provides `FeatureSettings` adapter supporting Dual-Engine configuration (per-feature model/endpoint overrides).
- Incremental first-run setup wizard and `code_continue_configure` command.
- Status bar widget manager (`update_status_bar`, `_refresh_all_status_bars`) showing model and completion activity.
- On-the-fly model switcher (`code_continue_switch_model`).

### utils/suggest.py
- Fill-In-The-Middle (FIM) & suffix-aware inline completions.
- Intelligent suffix overlap deduplication via `trim_suffix_overlap`.
- Live status bar indicator updates during generation.
- Implements `CodeContinueListener` (`on_activated`, `on_modified`, `on_text_command`, `on_query_context` for `code_continue_visible`).
- Implements `code_continue_suggest` and line-by-line `code_continue_accept`.

### utils/chat.py
- Interactive split-view Markdown chat panel (`code_continue_chat`).
- Real-time token streaming using Server-Sent Events (SSE).
- Quick Action presets: *Explain Selection*, *Find Bugs & Vulnerabilities*, *Generate Unit Tests*.
- Maintains conversation history, formats selected code, and renders assistant replies.

### utils/edit.py
- In-place natural language code rewrite and refactoring (`code_continue_edit`).
- Interactive Diff & Review: unified diff preview in a scratch tab before accepting.
- Preset refactoring actions: *Add Docstrings & Types*, *Optimize & Clean Code*.
- Selection target retention across tab switches and `code_continue_replace_selection`.

### utils/api.py
- Provider abstractions for OpenAI-compatible endpoints (`/v1/chat/completions`) and Anthropic Claude (`/v1/messages`).
- Streaming chunk parser (`parse_stream_chunk`).
- Endpoint normalization (`normalize_endpoint`), model endpoint deduction (`get_models_endpoint`), dynamic discovery (`fetch_models`), and connectivity test (`test_endpoint_connectivity`).

### utils/text_utils.py
- Pure Python text utilities: `compute_unified_diff`, `trim_suffix_overlap`, `clean_markdown_fences`, `strip_common_indent`, `describe_code_selection`.




# Package Structure for codeContinue

This document explains the structure of the codeContinue plugin for Sublime Text.

## Directory Layout

```
codeContinue/
├── codeContinue.py                    # Main plugin file
├── CodeContinue.sublime-settings      # Default settings template
├── Default.sublime-keymap             # Default keybindings
├── package-metadata.json              # Package Control metadata
├── messages.json                       # Post-install messages
├── messages/
│   ├── install.txt                    # Installation welcome message
│   └── 1.0.0.txt                      # Release notes for v1.0.0
├── README.md                          # User documentation
└── LICENSE                            # License file
```

## How It Works with Package Control

1. **Installation**: User installs via Package Control ( manually for now)
2. **First Launch**: `plugin_loaded()` detects first run
3. **Setup Wizard**: Shows input dialogs for endpoint & model
4. **Configuration Saved**: Settings saved to `CodeContinue.sublime-settings`
5. **Welcome Message**: Package Control shows `messages/install.txt`

## File Descriptions

### codeContinue.py
- Main plugin implementation
- Contains `plugin_loaded()` for first-run setup
- Handles suggestion requests and display
- Manages phantom rendering and acceptance

### CodeContinue.sublime-settings
- Template with default values
- Users' settings are saved here automatically on first run
- Customizable via Preferences > Package Settings > codeContinue

### Default.sublime-keymap
- Default keybindings: Tab (accept)
- Users can override in their own keymap

### messages.json & messages/
- Package Control feature for post-installation messaging
- Shows welcome guide and release notes
- Improves user onboarding

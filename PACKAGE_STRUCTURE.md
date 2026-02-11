# Package Structure for codeContinue

This document explains the structure of the codeContinue plugin for Sublime Text.

## Directory Layout

```
codeContinue/
├── codeContinue.py                    # Main plugin file
├── CodeContinue.sublime-settings      # Default settings template
├── Default.sublime-commands           # Command palette entries
├── Default.sublime-keymap             # Default keybindings
├── Main.sublime-menu                  # Package Settings menu
├── messages.json                      # Post-install messages
├── messages/
│   ├── install.txt                    # Installation welcome message
│   └── 1.1.0.txt                      # Release notes for v1.1.0
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
- Template with default values and documentation comments
- Users' settings are saved automatically to the User package
- Customizable via Preferences > Package Settings > CodeContinue

### Default.sublime-commands
- Command palette entries for Configure, Suggest, Settings, and Key Bindings

### Default.sublime-keymap
- Default keybindings (empty by default to avoid conflicts)
- Users can add bindings via Preferences > Package Settings > CodeContinue > Key Bindings

### Main.sublime-menu
- Adds CodeContinue to Preferences > Package Settings menu
- Exposes Settings, Key Bindings, and Configure Wizard

### messages.json & messages/
- Package Control feature for post-installation messaging
- Shows welcome guide and release notes
- Improves user onboarding


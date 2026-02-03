# CodeContinue Installation Tools for Experiments/Dev

This directory contains standalone installers for CodeContinue. These scripts are **not loaded by Sublime Text** - they are meant to be run with your system Python.

## Installation Methods

### Option 1: GUI Installer (Recommended)

```bash
python install_gui.py
```

Requires `tkinter` (usually included with Python on Windows/macOS, may need `python3-tk` on Linux).

### Option 2: CLI Installer

```bash
python install.py
```

## What the installers do

1. Detect your Sublime Text 4 installation
2. Locate your Packages directory
3. Configure API settings (endpoint, model, API key)
4. **Select your preferred keybinding** for accepting suggestions
5. Copy CodeContinue files to the Packages directory

## Keybinding Options

During installation, you can choose from:
- **Tab** - Accept with Tab key
- **Right Arrow** - Accept with Right arrow key  
- **Ctrl+Enter** - Accept with Ctrl+Enter
- **End** - Accept with End key

## Note

For Package Control users, the package is installed automatically. These tools are for manual installation only.

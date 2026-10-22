# CodeContinue Troubleshooting Guide

This guide covers common issues, debugging workflows, and setup verification.

---

## 1. Setup Wizard Not Appearing
* **Command Palette**: Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS) and type `CodeContinue: Configure`.
* **Menu**: Navigate to `Preferences > Package Settings > CodeContinue > Configure Wizard...`.
* **Restart**: If just installed, restart Sublime Text (`File > Exit`, then reopen).

---

## 2. Suggestions Not Appearing
1. **Trigger Keybinding**: By default, CodeContinue triggers on-demand via `Ctrl+Enter` (and accepts with `Tab`). Ensure your keybindings are configured (run `CodeContinue: Configure` and select the recommended preset).
2. **File Syntax**: Check that the current tab has a syntax recognized in `trigger_language` (e.g. Python, C++, JavaScript). Unsaved or "Plain Text" buffers do not trigger suggestions by default. Set the syntax via `Ctrl+Shift+P` >> `Set Syntax: Python`.
3. **Check Connection**: Verify your LLM server is running and reachable.
4. **Enable Debug Mode**:
   - Open settings (`Ctrl+Shift+P` >> `Preferences: CodeContinue Settings`).
   - Set `"debug": true`.
   - Open Sublime Text's console via `View > Show Console` (or ``Ctrl+` ``) to inspect outgoing requests and server replies in real time.

---

## 3. Package Control Updates Not Taking Effect (Manual Install Conflict)
If you previously installed CodeContinue manually (e.g. via `python tools/install.py` or by copying files into `Packages/`), Sublime Text prioritizes the unpacked `Packages/CodeContinue` directory over Package Control's automatically updated `.sublime-package` archive. As a result, newer updates downloaded by Package Control will be ignored.

### How to Fix:
Delete the manual override folder so Sublime Text falls back to Package Control's auto-updated package:

* **macOS**:
  ```bash
  rm -rf "$HOME/Library/Application Support/Sublime Text/Packages/CodeContinue"
  ```
* **Windows**:
  - *PowerShell*:
    ```powershell
    Remove-Item -Recurse -Force "$env:APPDATA\Sublime Text\Packages\CodeContinue"
    ```
  - *Command Prompt*:
    ```cmd
    rmdir /s /q "%APPDATA%\Sublime Text\Packages\CodeContinue"
    ```
* **Linux**:
  ```bash
  rm -rf ~/.config/sublime-text/Packages/CodeContinue
  ```

Restart Sublime Text after removing the folder.

---

## 4. Timeout Errors
* If using larger local models (e.g. 7B+ parameters) or remote endpoints under high load, increase `timeout_ms` in `CodeContinue.sublime-settings`:
  ```json
  "timeout_ms": 60000
  ```
* Ensure your local LLM runner (LM Studio, Ollama, etc.) is active and not stuck generating another response.

---

## 5. Authentication & Connection Errors
* **HTTP 401 / 403**: Verify your `api_key` in settings.
* **Connection Refused**: Ensure the local server is listening on the expected host/port (e.g. `http://localhost:1234` or `http://localhost:8000`).
* **IPv6 / Localhost**: On macOS or Linux, try replacing `localhost` with `127.0.0.1` (e.g. `http://127.0.0.1:8000/v1/chat/completions`) if your runner only binds to IPv4.

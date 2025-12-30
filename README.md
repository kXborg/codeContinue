# CodeContinue - AI Code Completion for Sublime Text

An LLM-powered Sublime Text plugin that provides intelligent inline code completion suggestions using OpenAI-compatible APIs.

## Features

- Fast inline code completion powered by your choice of LLM
- Simple keyboard shortcuts: `Ctrl+Enter` to suggest, `Tab` to accept
- Context-aware suggestions based on surrounding code
- Configurable for multiple languages (Python, C++, JavaScript, etc.)
- Works with any OpenAI-compatible API endpoint

## Installation

### Option 1: Automated Installer (Recommended)

We provide cross-platform installers for Windows, macOS, and Linux:

#### Python CLI Installer
```bash
python install.py
```
Interactive command-line installer. Detects Sublime Text automatically, walks you through configuration.

#### GUI Installer
```bash
python install_gui.py
```
Graphical installer with Tkinter. Pre-loads existing settings, configurable interface.

**Both installers:**
- ✓ Auto-detect Sublime Text 4 installation
- ✓ Install to correct Packages directory
- ✓ Pre-configure API endpoint, model, and settings
- ✓ Cross-platform (Windows, macOS, Linux)

### Option 2: Package Control (Coming Soon)

1. Open Sublime Text
2. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
3. Type "Package Control: Install Package"
4. Search for "codeContinue"
5. Press Enter to install

The plugin will automatically prompt you to enter your API endpoint and model on first launch.

### Option 3: Manual Installation

If you prefer manual setup:

1. **Create the plugin directory:**
   ```
   Windows: C:\Users\[User]\AppData\Roaming\Sublime Text\Packages\CodeContinue
   macOS: ~/Library/Application Support/Sublime Text/Packages/CodeContinue
   Linux: ~/.config/sublime-text/Packages/CodeContinue
   ```

2. **Copy all plugin files:**
   - `codeContinue.py`
   - `CodeContinue.sublime-settings`
   - `Default.sublime-keymap`
   - `Default.sublime-commands`
   - `messages.json`
   - `messages/` directory

3. **Restart Sublime Text**
   - The setup wizard will appear automatically on first run

## First-Run Setup

When you launch Sublime Text after installing codeContinue, a setup wizard appears automatically:

1. **Enter your API endpoint** (v1 compatible)
   - Example: `https://api.openai.com/v1/chat/completions` for OpenAI
   - Or: `http://localhost:8000/v1/chat/completions` for local servers
   - Or any OpenAI-compatible endpoint

2. **Enter your model name**
   - Examples: `gpt-3.5-turbo`, `gpt-4` (OpenAI)
   - Or: `Qwen/Qwen2.5-Coder-1.5B-Instruct` (Hugging Face)
   - Or any model available on your endpoint

3. **Enter API key (optional)**
   - Only needed for endpoints requiring authentication
   - Leave blank if your endpoint doesn't require it

Once configured, you're ready to use! All settings are saved automatically to `CodeContinue.sublime-settings`.

## Configuration

### Automatic Setup (First Run)

The setup wizard automatically appears when you first install the plugin. It will ask for:
- API endpoint URL
- Model name
- API key (optional)

Settings are saved automatically.

### Reconfigure Anytime

You can change your settings at any time using the command palette:

1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS, `Ctrl+Shift+P` on Linux)
2. Type "CodeContinue: Configure"
3. Follow the prompts to update:
   - API endpoint
   - Model name
   - API key (optional)

Changes are saved immediately.

### Manual Configuration

For advanced users, edit settings directly:

1. Go to `Preferences > Package Settings > CodeContinue > Settings`
2. Edit the JSON file:

```json
{
    "endpoint": "https://api.openai.com/v1/chat/completions",
    "model": "gpt-3.5-turbo",
    "api_key": "sk-...",
    "max_context_lines": 30,
    "timeout_ms": 20000,
    "trigger_language": ["python", "cpp", "javascript"]
}
```

### Configuration Options

- **endpoint**: Your OpenAI-compatible API endpoint (v1 format) - **Required**
  - OpenAI: `https://api.openai.com/v1/chat/completions`
  - Local server: `http://localhost:8000/v1/chat/completions`
  - Other providers: Use their v1-compatible endpoint

- **model**: The model to use for completions - **Required**
  - Examples: `gpt-3.5-turbo`, `gpt-4`, `Qwen/Qwen2.5-Coder-1.5B-Instruct`, etc.

- **api_key**: Authentication key (optional)
  - Only needed if your endpoint requires it
  - For OpenAI: `sk-...`
  - Leave blank if not needed

- **max_context_lines**: Number of lines of context to send (default: 30)
  - Increase for more context, decrease for faster responses

- **timeout_ms**: Request timeout in milliseconds (default: 20000)
  - Increase if using slower endpoints

- **trigger_language**: Array of language scopes to enable the plugin
  - Examples: `python`, `cpp`, `javascript`, `typescript`, `java`, `go`, `rust`, etc.

### API Authentication

For endpoints requiring authentication (like OpenAI):

1. **Using the Configure command:**
   - Press `Ctrl+Shift+P` → "CodeContinue: Configure"
   - When prompted for API Key, enter your key (e.g., `sk-...` for OpenAI)
   - Settings are saved automatically

2. **Or edit settings directly:**
   - Open `Preferences > Package Settings > CodeContinue > Settings`
   - Add your API key:
   ```json
   {
       "api_key": "sk-your-api-key-here"
   }
   ```

## Usage

### Getting Suggestions

1. **Trigger a suggestion:**
   - Press `Ctrl+Enter` while editing code (Windows/Linux)
   - Or press `Cmd+Enter` on macOS
   - The plugin analyzes surrounding code and fetches a suggestion
   - The suggestion appears in gray text inline

2. **Auto-suggest on new line:**
   - The plugin also triggers automatically when you press `Enter` at the end of a line
   - This provides a smooth, natural workflow

### Accepting Suggestions

1. **Accept the suggestion:**
   - Press `Right Arrow` to accept the suggestion
   - The code is inserted at your cursor position

2. **Accept multi-line suggestions:**
   - If a suggestion has multiple lines, press `Right Arrow` multiple times
   - Each press accepts the next line

3. **Dismiss a suggestion:**
   - Just keep typing or move your cursor
   - The suggestion will automatically disappear
   - Pressing `Escape` also dismisses it

### Why Right Arrow instead of Tab?

The `Right Arrow` key works better for code completion because:
- ✓ Allows you to press `Tab` for indentation without accepting the suggestion
- ✓ Cleaner workflow when mixing indentation and suggestions
- ✓ Natural cursor movement semantics

## Keybindings

Default keybindings (customizable in `Default.sublime-keymap`):

- `Ctrl+Enter` - Trigger code suggestion
- `Right Arrow` - Accept suggestion (only when phantom is visible)
- `Escape` - Dismiss suggestion

### Command Palette Commands

- `CodeContinue: Suggest` - Manually trigger a suggestion
- `CodeContinue: Configure` - Open configuration wizard

## Requirements

- Sublime Text 4
- Internet connection (for API access)
- Access to an OpenAI-compatible API endpoint

## Troubleshooting

### Setup wizard not appearing
- Restart Sublime Text: File → Exit, then reopen
- Check Sublime Text console (View → Show Console) for errors
- Manually run: `Preferences > Package Settings > CodeContinue > Settings`
- Or use `Ctrl+Shift+P` → "CodeContinue: Configure"

### Suggestions not appearing
- Check that your language is in the `trigger_language` list
- Verify your API endpoint is accessible and correct
- Check console for errors: `View → Show Console`
- Try `Ctrl+Shift+P` → "CodeContinue: Configure" to verify settings
- Make sure you have an active API key if required

### Timeout errors
- Increase `timeout_ms` in settings (default: 20000ms)
- Try a faster model or local endpoint
- Check your internet connection
- Verify your API key is valid

### Authentication/Connection errors
- Verify your API key is correct
- Make sure endpoint URL is exactly right (copy-paste to avoid typos)
- Check if the endpoint is currently running/available
- Use `Ctrl+Shift+P` → "CodeContinue: Configure" to update credentials

### "Right Arrow" keybinding not working
- Check that phantom is visible (gray text suggestion showing)
- The keybinding only works when a suggestion is displayed
- You can still use `Right Arrow` for normal cursor movement

## Advanced Configuration

### Custom API Endpoints

CodeContinue works with any OpenAI-compatible v1 API. Examples:

**OpenAI:**
```
endpoint: https://api.openai.com/v1/chat/completions
model: gpt-3.5-turbo or gpt-4
api_key: sk-...
```

**Local LLM (LLaMA, Mistral, etc.):**
```
endpoint: http://localhost:8000/v1/chat/completions
model: (whatever model you're running)
api_key: (usually not needed)
```

**Hugging Face Inference API:**
```
endpoint: https://api-inference.huggingface.co/v1/chat/completions
model: HuggingFaceH4/zephyr-7b-beta
api_key: hf_...
```

**Other providers:**
Any endpoint supporting OpenAI's v1 chat completion format will work.

### Customizing Keybindings

Edit `Preferences > Package Settings > CodeContinue > Key Bindings` to customize:

```json
[
    {
        "keys": ["ctrl+shift+l"],
        "command": "code_continue_suggest"
    },
    {
        "keys": ["shift+right"],
        "command": "code_continue_accept",
        "context": [
            {"key": "code_continue_visible", "operator": "equal", "operand": "true"}
        ]
    }
]
```

## Supported Models

CodeContinue works with any OpenAI-compatible endpoint. Some popular options:

**Free/Open Source:**
- Qwen/Qwen2.5-Coder (HuggingFace)
- Mistral AI (HuggingFace, Together AI)
- CodeLLaMA (Meta, various providers)
- DeepSeek Coder (HuggingFace)

**Paid APIs:**
- OpenAI (GPT-3.5, GPT-4)
- Anthropic Claude (via compatible endpoints)
- Together AI
- Modal
- Anyscale

**Local/Self-Hosted:**
- Ollama (local, free)
- LLaMA.cpp (local, free)
- vLLM (self-hosted)
- Text Generation WebUI (local)

## License

See [LICENSE](LICENSE) file for details.

## Contributing

Found a bug? Have a feature request? Open an issue on GitHub!

## Development

For the technical package structure and distribution information, see [PACKAGE_STRUCTURE.md](PACKAGE_STRUCTURE.md).

### Testing Installation

To test the plugin before submitting to Package Control:

1. **Using Python installers:**
   ```bash
   python install.py           # CLI installer
   python install_gui.py       # GUI installer
   ```

2. **Manual testing:**
   - Copy files to your Packages directory
   - Restart Sublime Text
   - Test the setup wizard and suggestions

3. **Cross-platform testing:**
   - Both installers work on Windows, macOS, and Linux
   - Test on each platform before release

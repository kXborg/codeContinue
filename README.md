# CodeContinue - AI Code Completion for Sublime Text

An LLM-powered Sublime Text plugin that provides intelligent inline code completion suggestions using OpenAI-compatible APIs.

## Features

- 🚀 Fast inline code completion powered by your choice of LLM
- ⌨️ Simple keyboard shortcuts: `Ctrl+Enter` to suggest, `Tab` to accept
- 🎯 Context-aware suggestions based on surrounding code
- 🔧 Configurable for multiple languages (Python, C++, JavaScript, etc.)
- 🌐 Works with any OpenAI-compatible API endpoint

## Installation

### Option 1: Package Control (Recommended)

1. Open Sublime Text
2. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
3. Type "Package Control: Install Package"
4. Search for "codeContinue"
5. Press Enter to install

The plugin will automatically prompt you to enter your API endpoint and model on first launch.

### Option 2: Manual Installation

1. **Create the plugin directory:**
   ```
   C:\Program Files\Sublime Text\Packages\codeContinue
   ```

2. **Copy the plugin file:**
   - Copy `codeContinue.py` to `C:\Program Files\Sublime Text\Packages\codeContinue\`

3. **Copy the settings file:**
   - Copy `CodeContinue.sublime-settings` to `C:\Program Files\Sublime Text\Packages\User\`

4. **Copy the keymap file (optional):**
   - Copy `Default.sublime-keymap` to `C:\Program Files\Sublime Text\Packages\User\`

5. **Restart Sublime Text**
   - The setup wizard will appear automatically on first run

## First-Run Setup

When you launch Sublime Text after installing codeContinue, a setup wizard will appear:

1. **Enter your API endpoint** (v1 compatible)
   - Example: `https://api.openai.com/v1/chat/completions`
   - Or: `http://localhost:8000/v1/chat/completions` for local servers

2. **Enter your model name**
   - Example: `gpt-3.5-turbo` for OpenAI
   - Or: `Qwen/Qwen2.5-Coder-1.5B-Instruct` for other providers

Once configured, you're ready to use! The settings are saved automatically.

## Configuration

### Automatic Setup (First Run)

The setup wizard automatically appears when you first install the plugin. Simply enter:
- Your API endpoint (v1 format)
- Your model name

Settings are saved automatically.

### Manual Configuration

To reconfigure or edit settings manually:

1. Go to `Preferences > Package Settings > codeContinue > Settings`
2. Edit the JSON file:

```json
{
    "endpoint": "https://api.openai.com/v1/chat/completions",
    "model": "gpt-3.5-turbo",
    "max_context_lines": 30,
    "timeout_ms": 20000,
    "trigger_language": ["python", "cpp", "javascript"]
}
```

### Configuration Options

- **endpoint**: Your OpenAI-compatible API endpoint (v1 format)
  - OpenAI: `https://api.openai.com/v1/chat/completions`
  - Local server: `http://localhost:8000/v1/chat/completions`
  - Other providers: Use their v1-compatible endpoint

- **model**: The model to use for completions
  - Examples: `gpt-3.5-turbo`, `gpt-4`, `Qwen/Qwen2.5-Coder-1.5B-Instruct`, etc.

- **max_context_lines**: Number of lines of context to send (default: 30)

- **timeout_ms**: Request timeout in milliseconds (default: 20000)

- **trigger_language**: Array of language scopes to enable the plugin
  - Examples: `python`, `cpp`, `javascript`, `typescript`, `java`, `go`, etc.

### API Authentication

For endpoints requiring authentication (like OpenAI), you'll need to add an API key. Edit `codeContinue.py` and add the header in the request:

```python
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_API_KEY_HERE'
}
```

## Usage

1. **Trigger a suggestion:**
   - Press `Ctrl+Enter` while editing code
   - Or press `Enter` at the end of a line for auto-suggestion
   - The plugin will show an inline suggestion in gray text

2. **Accept a suggestion:**
   - Press `Tab` to accept and insert the suggested code
   - If there are multiple lines, you can accept them one at a time

3. **Dismiss a suggestion:**
   - Just keep typing or move your cursor
   - The suggestion will disappear

## Keybindings

Default keybindings (customizable in `Default.sublime-keymap`):

- `Ctrl+Enter` - Trigger code suggestion
- `Tab` - Accept suggestion

## Requirements

- Sublime Text 4
- Internet connection (for API access)
- Access to an OpenAI-compatible API endpoint

## Troubleshooting

### Setup wizard not appearing
- Restart Sublime Text: File → Exit, then reopen
- Check Sublime Text console (View → Show Console) for errors
- Manually run: `Preferences > Package Settings > codeContinue > Settings`

### Suggestions not appearing
- Check that your language is in the `trigger_language` list
- Verify your API endpoint is accessible
- Check console for errors with `View → Show Console`

### Timeout errors
- Increase `timeout_ms` in settings (default: 20000ms)
- Try a faster model or local endpoint
- Check your internet connection

### Authentication errors
- Verify your API key is correct
- Make sure endpoint URL is exactly right
- Some providers require special headers (see Configuration Options below)

## Advanced Configuration

### API Authentication

For endpoints requiring authentication (like OpenAI), edit the `codeContinue.py` file and add the header in the `fetch_completion()` function:

```python
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_API_KEY_HERE'
}
req = urllib.request.Request(endpoint, data=json.dumps(data).encode(), headers=headers)
```

## License

See [LICENSE](LICENSE) file for details.

## Contributing

Found a bug? Have a feature request? Open an issue on GitHub!

## Development

For the technical package structure and distribution information, see [PACKAGE_STRUCTURE.md](PACKAGE_STRUCTURE.md).

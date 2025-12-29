# CodeContinue - AI Code Completion for Sublime Text

An LLM-powered Sublime Text plugin that provides intelligent inline code completion suggestions using OpenAI-compatible APIs.

## Features

- 🚀 Fast inline code completion powered by your choice of LLM
- ⌨️ Simple keyboard shortcuts: `Ctrl+Enter` to suggest, `Tab` to accept
- 🎯 Context-aware suggestions based on surrounding code
- 🔧 Configurable for multiple languages (Python, C++, JavaScript, etc.)
- 🌐 Works with any OpenAI-compatible API endpoint

## Installation

### Manual Installation

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
   - Or customize the keybindings in your existing keymap file

5. **Restart Sublime Text**

## Configuration

Edit the settings file at `C:\Program Files\Sublime Text\Packages\User\CodeContinue.sublime-settings`:

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
   - Press `Ctrl+Enter` while editing code or just `Enter `
   - The plugin will show an inline suggestion in gray text

2. **Accept a suggestion:**
   - Press `Tab` to accept and insert the suggested code

3. **Dismiss a suggestion:**
   - Just keep typing or move your cursor

4. **Auto-trigger on newline:**
   - Press `Enter` to automatically trigger suggestions for the next line

## Keybindings

Default keybindings (customizable in `Default.sublime-keymap`):

- `Ctrl+Enter` - Trigger code suggestion
- `Tab` - Accept suggestion

## Requirements

- Sublime Text 4
- Internet connection (for API access)
- Access to an OpenAI-compatible API endpoint

## Troubleshooting

### Suggestions not appearing
- Check that your language is in the `trigger_language` list
- Verify your API endpoint is accessible
- Check Sublime Text console (View → Show Console) for errors

### Timeout errors
- Increase `timeout_ms` in settings
- Try a faster model or local endpoint

### Authentication errors
- Verify your API key is correct
- Ensure the Authorization header is properly set

## License

See [LICENSE](LICENSE) file for details.

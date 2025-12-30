# CodeContinue - AI Code Completion for Sublime Text

An LLM-powered Sublime Text plugin that provides intelligent inline code completion suggestions using OpenAI-compatible APIs.

## Features

- Fast inline code completion powered by your choice of LLM
- Simple keyboard shortcuts: Just `Enter` to suggest, `Tab` to accept
- Context-aware suggestions based on surrounding code
- Configurable for multiple languages (Python, C++, JavaScript, etc.)
- Works with any OpenAI-compatible API endpoint

⚠️ Key-binding Disclaimer: We know we should not publish with keybindings, but `Tab` key rarely conflicts with other plugins. If it creates any issue, please change to other keys. Check below for guidelines.

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
   - **Note:** You must configure this - no default endpoint is provided

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

Settings are saved automatically. Reconfigure Anytime with  `Ctrl+Shift+P`.

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

### Default Keybinding

⚠️ Key-binding Disclaimer: We know we should not publish with keybindings, but `Tab` key rarely conflicts with other plugins. If it creates any issue, please change to other keys.

- **Tab** - Accept suggestion

**Customizing the keybinding:**
If `Tab` conflicts with your workflow, you can change it:

1. Go to `Preferences > Package Settings > CodeContinue > Key Bindings`
2. Modify the keybinding:
   ```json
   [
       {
           "keys": ["right"],  // or "ctrl+right", "end", etc.
           "command": "code_continue_accept"
       }
   ]
   ```

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

### Keybindings not working
- Make sure you've set up keybindings (they're not enabled by default)
- Go to `Preferences > Package Settings > CodeContinue > Key Bindings`
- Check for conflicts with other packages
- Try alternative key combinations

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

## License

See [LICENSE](LICENSE) file for details.

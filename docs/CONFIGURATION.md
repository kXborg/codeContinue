# CodeContinue Configuration Guide

Settings are stored in `Packages/User/CodeContinue.sublime-settings`. You can edit them directly via:
- `Preferences > Package Settings > CodeContinue > Settings`
- Or Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) >> `Preferences: CodeContinue Settings`

You can also re-run the interactive wizard anytime via `CodeContinue: Configure` or switch models on the fly with `CodeContinue: Switch Model...`.

---

## Settings Reference

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `endpoint` | string | `"http://localhost:8000/v1/chat/completions"` | Base OpenAI-compatible completions endpoint URL (**Required**). |
| `model` | string | `""` | Model identifier to use for completions (**Required**). |
| `api_key` | string | `""` | API key for authentication (optional, leave blank for local servers). |
| `chat_endpoint` | string | `""` | Dual-Engine override: endpoint for Chat (inherits `endpoint` if blank). |
| `chat_model` | string | `""` | Dual-Engine override: model for Chat (inherits `model` if blank). |
| `chat_api_key` | string | `""` | Dual-Engine override: API key for Chat (inherits `api_key` if blank). |
| `edit_endpoint` | string | `""` | Dual-Engine override: endpoint for Edit Selection (inherits `endpoint` if blank). |
| `edit_model` | string | `""` | Dual-Engine override: model for Edit Selection (inherits `model` if blank). |
| `edit_api_key` | string | `""` | Dual-Engine override: API key for Edit Selection (inherits `api_key` if blank). |
| `stream` | boolean | `true` | Stream chat responses in real-time using Server-Sent Events (SSE). |
| `status_bar` | boolean | `true` | Display active model and status widget in Sublime Text's bottom status bar. |
| `confirm_edits` | boolean | `true` | Require interactive confirmation and unified diff review before applying code edits. |
| `max_context_lines` | integer | `30` | Number of surrounding lines of code sent as context to the model. |
| `timeout_ms` | integer | `30000` | Request timeout in milliseconds (increase for slower or larger local models). |
| `trigger_language` | array | `["python", "cpp", "javascript"]` | Supported syntax languages/scopes (supports aliases like `c++`, `py`, `ts`, `js`, or `["*"]`). |
| `auto_suggest_on_enter`| boolean | `false` | When `false`, suggestions only trigger on-demand via shortcut. When `true`, triggers on `Enter`. |
| `system_prompt` | string | `""` | Custom system prompt for inline completions. Leave blank to use built-in default expert prompt. |
| `debug` | boolean | `false` | Enable verbose logging to Sublime Text console (`View > Show Console`). |

---

## Provider Recipes

### 1. Local LM Studio
Start LM Studio, load your model, and start the local server (default port `1234`):
```json
{
    "endpoint": "http://localhost:1234/v1/chat/completions",
    "model": "qwen2.5-coder-3b-instruct"
}
```

### 2. Local Ollama
Run `ollama serve` (default port `11434`):
```json
{
    "endpoint": "http://localhost:11434/v1/chat/completions",
    "model": "qwen2.5-coder:3b"
}
```

### 3. OpenAI
Direct cloud connection to OpenAI:
```json
{
    "endpoint": "https://api.openai.com/v1/chat/completions",
    "model": "gpt-4o",
    "api_key": "sk-your-openai-api-key"
}
```

### 4. Anthropic
Direct cloud connection using Anthropic's Messages API:
```json
{
    "endpoint": "https://api.anthropic.com/v1/messages",
    "model": "claude-3-5-sonnet-20241022",
    "api_key": "sk-ant-your-anthropic-key"
}
```

### 5. Dual-Engine Setup (Fast Local Completions + Powerful Cloud Chat & Edit)
Use a low-latency local model for real-time autocomplete, while offloading code review, unit test generation, and deep refactoring to a flagship cloud model:
```json
{
    // Fast local engine for inline completions
    "endpoint": "http://localhost:8000/v1/chat/completions",
    "model": "qwen2.5-coder:1.5b",

    // Flagship cloud engine for Chat about Selection
    "chat_endpoint": "https://api.anthropic.com/v1/messages",
    "chat_model": "claude-3-5-sonnet-20241022",
    "chat_api_key": "sk-ant-your-anthropic-key",

    // Flagship cloud engine for In-Place Code Editing
    "edit_endpoint": "https://api.openai.com/v1/chat/completions",
    "edit_model": "gpt-4o",
    "edit_api_key": "sk-your-openai-api-key"
}
```

# CodeContinue - AI Code Completion for VSCode

[![Version](https://img.shields.io/badge/version-0.0.1-blue.svg)](https://github.com/kXborg/codeContinue)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**CodeContinue** is an LLM-powered VSCode extension that provides intelligent inline code completion suggestions using OpenAI-compatible APIs. Take control of your coding experience with privacy-focused, customizable AI assistance.

> 🎉 **Production Ready**: This extension is fully functional with comprehensive error handling, state management, and long-term reliability features.

---

## 📖 About

CodeContinue brings AI-powered code completion to VSCode, inspired by the [Sublime Text plugin](https://github.com/kXborg/codeContinue) of the same name. Unlike cloud-based solutions, CodeContinue gives you:

- **🔒 Privacy**: Use your own API endpoint or local LLM
- **⚡ Speed**: Fast, context-aware suggestions
- **🎯 Control**: Configure exactly when and how suggestions appear
- **🛠️ Flexibility**: Works with any OpenAI-compatible API (OpenAI, Anthropic, local models via vLLM, etc.)

---

## ✨ Features

### Core Functionality
- **Inline Code Completion**: Get AI-powered suggestions as you type
- **Context-Aware**: Analyzes surrounding code for relevant suggestions
- **Multi-Language Support**: Works with Python, JavaScript, TypeScript, C++, Java, Go, Rust, and more
- **Customizable Triggers**: Configure which languages trigger auto-completion

### User Experience
- **First-Run Setup Wizard**: Easy configuration on first launch
- **Keyboard Shortcuts**: 
  - Press `Enter` to trigger suggestions (in configured languages)
  - Press `Tab` to accept suggestions
  - Press `Esc` to clear suggestions
  - Press `Ctrl+Enter` (or `Cmd+Enter` on Mac) for manual trigger
- **User-Friendly Error Messages**: Clear feedback when things go wrong
- **Debug Logging**: Built-in logging system for troubleshooting

### Reliability
- **Comprehensive Error Handling**: Never crashes, always recovers gracefully
- **Rate Limiting**: Prevents spam requests (configurable, default 1000ms)
- **Request Deduplication**: Cancels stale requests automatically
- **Memory Leak Prevention**: Automatic cleanup of closed documents
- **Timeout Management**: Proper 10-second timeout with cleanup
- **No Conflicts**: Automatically disables default inline suggestions to prevent interference

### Privacy & Security
- **Your API, Your Data**: Use your own endpoint
- **Local Model Support**: Works with locally hosted LLMs
- **Optional API Key**: Configure authentication if needed
- **No Telemetry**: Your code stays private

---

## 🚀 Quick Start

### Installation

1. **Clone or download** this repository
2. **Open in VSCode**: `code codecontinue`
3. **Install dependencies**: `npm install`
4. **Compile**: `npm run compile`
5. **Launch**: Press `F5` to open Extension Development Host

### First-Time Setup

1. When the extension activates, you'll see a welcome message
2. Click **"Configure Now"**
3. Enter your API endpoint (e.g., `https://api.openai.com/v1/chat/completions`)
4. Enter your model name (e.g., `gpt-3.5-turbo`)
5. Enter your API key (optional, press Enter to skip)
6. Done! Start coding with AI assistance

### Basic Usage

1. **Open a code file** (Python, JavaScript, etc.)
2. **Start typing** your code
3. **Press Enter** → AI suggestion appears as gray text
4. **Press Tab** → Accept the suggestion
5. **Press Esc** → Clear the suggestion

---

## ⚙️ Configuration

### Quick Configuration

Open Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P`) and run:
```
CodeContinue: Configure
```

### Settings

All settings are available in VSCode settings (`Ctrl+,` or `Cmd+,`):

| Setting | Default | Description |
|---------|---------|-------------|
| `codeContinue.endpoint` | `""` | OpenAI-compatible API endpoint URL |
| `codeContinue.model` | `"gpt-3.5-turbo"` | Model name to use for completions |
| `codeContinue.apiKey` | `""` | API key for authentication (optional) |
| `codeContinue.maxContextLines` | `40` | Maximum lines of context to send (before + after cursor) |
| `codeContinue.timeoutMs` | `10000` | Request timeout in milliseconds (10 seconds) |
| `codeContinue.triggerLanguages` | `[...]` | Languages that trigger auto-completion on Enter |
| `codeContinue.rateLimitMs` | `1000` | Minimum time between requests (prevents spam) |
| `codeContinue.enableLogging` | `false` | Enable debug logging to output channel |
| `codeContinue.temperature` | `0.3` | LLM temperature (0 = deterministic, 2 = creative) |
| `codeContinue.maxTokens` | `1024` | Maximum tokens in completion response |
| `codeContinue.disableDefaultInlineSuggest` | `true` | Disable VSCode's default inline suggestions (prevents conflicts) |

### Example Configuration

#### For OpenAI
```json
{
  "codeContinue.endpoint": "https://api.openai.com/v1/chat/completions",
  "codeContinue.model": "gpt-3.5-turbo",
  "codeContinue.apiKey": "sk-..."
}
```

#### For Local LLM (vLLM, Ollama, etc.)
```json
{
  "codeContinue.endpoint": "http://localhost:8000/v1/chat/completions",
  "codeContinue.model": "codellama-7b",
  "codeContinue.apiKey": ""
}
```

#### For Anthropic Claude
```json
{
  "codeContinue.endpoint": "https://api.anthropic.com/v1/messages",
  "codeContinue.model": "claude-3-sonnet-20240229",
  "codeContinue.apiKey": "sk-ant-..."
}
```

### Trigger Languages

Default languages that trigger auto-completion:
- Python
- JavaScript / TypeScript / React
- C / C++
- Java
- Go
- Rust
- PHP
- Ruby
- Swift
- Kotlin
- C#

**Customize**: Edit `codeContinue.triggerLanguages` in settings to add/remove languages.

---

## 🎮 Commands

| Command | Keybinding | Description |
|---------|------------|-------------|
| `CodeContinue: Configure` | - | Open configuration wizard |
| `CodeContinue: Suggest` | `Ctrl+Enter` (`Cmd+Enter` on Mac) | Manually trigger suggestion |
| `CodeContinue: Clear Suggestion` | `Esc` | Clear current suggestion |
| `CodeContinue: Show Logs` | - | Open debug output channel |

---

## 🔧 Advanced Usage

### Adjusting Rate Limiting

If suggestions are too frequent or too rare:
```json
{
  "codeContinue.rateLimitMs": 2000  // 2 seconds between requests
}
```

### Increasing Timeout for Slow APIs

If you get timeout errors:
```json
{
  "codeContinue.timeoutMs": 30000  // 30 seconds
}
```

### Enabling Debug Logging

For troubleshooting:
```json
{
  "codeContinue.enableLogging": true
}
```
Then view logs: `Ctrl+Shift+P` → "CodeContinue: Show Logs"

### Customizing Context Size

More context = better suggestions, but slower:
```json
{
  "codeContinue.maxContextLines": 80  // Send 80 lines of context
}
```

### Adjusting Creativity

More creative suggestions:
```json
{
  "codeContinue.temperature": 0.7  // More creative (0.0 - 2.0)
}
```

---

## 🐛 Troubleshooting

### No suggestions appearing?

1. **Check configuration**: Run `CodeContinue: Configure`
2. **Enable logging**: Set `codeContinue.enableLogging: true`
3. **View logs**: Run `CodeContinue: Show Logs`
4. **Check language**: Ensure your file's language is in `triggerLanguages`

### Timeout errors?

- **Increase timeout**: Set `codeContinue.timeoutMs: 30000` (30 seconds)
- **Check network**: Ensure you can reach the API endpoint
- **Try local model**: Consider using a faster local LLM

### Authentication errors?

- **Check API key**: Verify `codeContinue.apiKey` is correct
- **Check endpoint**: Ensure endpoint URL is valid
- **Check permissions**: Verify API key has necessary permissions

### Suggestions in wrong language?

- **Check trigger list**: Edit `codeContinue.triggerLanguages`
- **Add your language**: Include the language ID (e.g., `"markdown"`)

### Too many/few requests?

- **Adjust rate limit**: Change `codeContinue.rateLimitMs`
- **Default is 1000ms** (1 second between requests)

---

## 📊 Requirements

- **VSCode**: Version 1.108.1 or higher
- **API Endpoint**: OpenAI-compatible API (OpenAI, Anthropic, local LLM, etc.)
- **API Key**: Optional, depending on your endpoint
- **Internet**: Required for cloud APIs, not needed for local models

---

## 🏗️ Architecture

CodeContinue is built with reliability and maintainability in mind:

```
src/
├── extension.ts           - Entry point, commands, lifecycle management
├── api.ts                 - API client with comprehensive error handling
├── completionProvider.ts  - Inline completion logic
├── state.ts               - State management and rate limiting
├── logger.ts              - Logging system
└── utils.ts               - Utility functions (markdown cleaning, indent normalization)
```

## 📝 Known Issues

- **Multi-line line-by-line acceptance**: Not yet implemented (planned for Phase 2)
  - Currently, suggestions are accepted all at once
  - Future: Accept one line at a time with Tab key

---

## 🗺️ Roadmap

### Phase 2 (Planned)
- Multi-line line-by-line acceptance
- Suggestion caching
- Multiple suggestion variants
- Custom prompt templates
- Usage analytics

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 🙏 Acknowledgments

This VSCode extension is based on my [CodeContinue Sublime Text plugin](https://github.com/kXborg/codeContinue).

---

## 🤝 Contributing

Contributions are welcome! Please feel free to:
- Report bugs
- Suggest features
- Submit pull requests
- Improve documentation

---

## 🎯 Why CodeContinue?

### Privacy First
- **Your API**: Use your own endpoint
- **Your Data**: Code never leaves your control
- **No Telemetry**: No tracking, no analytics

### Developer Friendly
- **Fast**: Optimized for speed
- **Reliable**: Never crashes, comprehensive error handling
- **Configurable**: Customize every aspect

### Open Source
- **Transparent**: All code is open
- **Extensible**: Easy to modify and extend
- **Community**: Contributions welcome



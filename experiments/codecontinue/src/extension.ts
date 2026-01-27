import * as vscode from "vscode";
import { CodeContinueProvider } from "./completionProvider";
import { initLogger, log, showLog, disposeLogger } from "./logger";
import { canMakeRequest, cleanupDocument } from "./state";

// Store original inline suggest setting to restore on deactivation
let originalInlineSuggestSetting: boolean | undefined;

/**
 * Extension activation
 * Called when the extension is first activated
 */
export function activate(context: vscode.ExtensionContext) {
  // Initialize logger
  initLogger();
  log("CodeContinue extension activated");

  // Disable default inline suggestions if configured
  disableDefaultInlineSuggestions();

  // Register inline completion provider for all files
  const provider = vscode.languages.registerInlineCompletionItemProvider(
    { pattern: "**" },
    new CodeContinueProvider()
  );
  context.subscriptions.push(provider);

  // Register configure command
  const configureCommand = vscode.commands.registerCommand(
    "codecontinue.configure",
    async () => {
      await showConfigurationWizard();
    }
  );
  context.subscriptions.push(configureCommand);

  // Register manual suggest command
  const suggestCommand = vscode.commands.registerCommand(
    "codecontinue.suggest",
    () => {
      log("Manual suggestion triggered");
      vscode.commands.executeCommand("editor.action.inlineSuggest.trigger");
    }
  );
  context.subscriptions.push(suggestCommand);

  // Register clear suggestion command
  const clearCommand = vscode.commands.registerCommand(
    "codecontinue.clearSuggestion",
    () => {
      log("Clearing inline suggestions");
      vscode.commands.executeCommand("editor.action.inlineSuggest.hide");
    }
  );
  context.subscriptions.push(clearCommand);

  // Register show logs command
  const showLogsCommand = vscode.commands.registerCommand(
    "codecontinue.showLogs",
    () => {
      showLog();
    }
  );
  context.subscriptions.push(showLogsCommand);

  // Listen for Enter key to trigger suggestions (with language filtering and rate limiting)
  const documentChangeListener = vscode.workspace.onDidChangeTextDocument((event) => {
    handleDocumentChange(event);
  });
  context.subscriptions.push(documentChangeListener);

  // Clean up state when documents are closed (prevent memory leaks)
  const documentCloseListener = vscode.workspace.onDidCloseTextDocument((document) => {
    cleanupDocument(document);
    log(`Cleaned up state for closed document: ${document.uri.fsPath}`);
  });
  context.subscriptions.push(documentCloseListener);

  // Show first-run setup wizard if not configured
  checkFirstRun();

  log("CodeContinue extension fully initialized");
}

/**
 * Extension deactivation
 * Called when the extension is deactivated
 */
export function deactivate() {
  log("CodeContinue extension deactivated");

  // Restore original inline suggest setting
  restoreDefaultInlineSuggestions();

  disposeLogger();
}

/**
 * Disable VSCode's default inline suggestions if configured
 */
function disableDefaultInlineSuggestions(): void {
  const config = vscode.workspace.getConfiguration("codeContinue");
  const shouldDisable = config.get<boolean>("disableDefaultInlineSuggest", true);

  if (!shouldDisable) {
    log("Default inline suggestions will remain enabled (user preference)");
    return;
  }

  // Get current setting
  const editorConfig = vscode.workspace.getConfiguration("editor");
  originalInlineSuggestSetting = editorConfig.get<boolean>("inlineSuggest.enabled");

  // Only disable if it's currently enabled
  if (originalInlineSuggestSetting !== false) {
    editorConfig.update(
      "inlineSuggest.enabled",
      false,
      vscode.ConfigurationTarget.Global
    ).then(() => {
      log(`Disabled default inline suggestions (original: ${originalInlineSuggestSetting})`);
    });
  } else {
    log("Default inline suggestions already disabled");
  }
}

/**
 * Restore VSCode's default inline suggestions to original state
 */
function restoreDefaultInlineSuggestions(): void {
  const config = vscode.workspace.getConfiguration("codeContinue");
  const shouldDisable = config.get<boolean>("disableDefaultInlineSuggest", true);

  // Only restore if we disabled it
  if (!shouldDisable || originalInlineSuggestSetting === undefined) {
    return;
  }

  const editorConfig = vscode.workspace.getConfiguration("editor");
  editorConfig.update(
    "inlineSuggest.enabled",
    originalInlineSuggestSetting,
    vscode.ConfigurationTarget.Global
  ).then(() => {
    log(`Restored default inline suggestions to: ${originalInlineSuggestSetting}`);
  });
}

/**
 * Handle document changes to trigger suggestions on Enter key
 * @param event - The document change event
 */
function handleDocumentChange(event: vscode.TextDocumentChangeEvent) {
  // Check if there's a change
  const change = event.contentChanges[0];
  if (!change) {
    return;
  }

  // Only trigger on newline insertion
  if (change.text !== "\n") {
    return;
  }

  // Get active editor
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document !== event.document) {
    return;
  }

  const document = editor.document;
  const languageId = document.languageId;

  // Check if language is in trigger list
  const config = vscode.workspace.getConfiguration("codeContinue");
  const triggerLanguages = config.get<string[]>("triggerLanguages", []);

  if (!triggerLanguages.includes(languageId)) {
    log(`Skipping trigger for language: ${languageId} (not in trigger list)`);
    return;
  }

  // Check rate limit
  const rateLimitMs = config.get<number>("rateLimitMs", 1000);
  if (!canMakeRequest(document, rateLimitMs)) {
    log(`Skipping trigger due to rate limit (${rateLimitMs}ms)`);
    return;
  }

  log(`Triggering suggestion for ${languageId} after Enter key`);

  // Small delay to let cursor move to new line
  setTimeout(() => {
    vscode.commands.executeCommand("editor.action.inlineSuggest.trigger");
  }, 50);
}

/**
 * Show configuration wizard with input boxes
 */
async function showConfigurationWizard(): Promise<void> {
  const config = vscode.workspace.getConfiguration("codeContinue");

  // Step 1: Endpoint
  const currentEndpoint = config.get<string>("endpoint", "");
  const endpoint = await vscode.window.showInputBox({
    prompt: "Enter your OpenAI-compatible API endpoint URL",
    value: currentEndpoint,
    placeHolder: "https://api.openai.com/v1/chat/completions",
    validateInput: (value) => {
      if (!value || value.trim() === "") {
        return "Endpoint URL is required";
      }
      try {
        new URL(value);
        return null;
      } catch {
        return "Please enter a valid URL";
      }
    }
  });

  if (!endpoint) {
    vscode.window.showInformationMessage("Configuration cancelled");
    return;
  }

  await config.update("endpoint", endpoint, vscode.ConfigurationTarget.Global);
  log(`Endpoint configured: ${endpoint}`);

  // Step 2: Model
  const currentModel = config.get<string>("model", "gpt-3.5-turbo");
  const model = await vscode.window.showInputBox({
    prompt: "Enter the model name to use",
    value: currentModel,
    placeHolder: "gpt-3.5-turbo",
    validateInput: (value) => {
      if (!value || value.trim() === "") {
        return "Model name is required";
      }
      return null;
    }
  });

  if (!model) {
    vscode.window.showInformationMessage("Configuration cancelled");
    return;
  }

  await config.update("model", model, vscode.ConfigurationTarget.Global);
  log(`Model configured: ${model}`);

  // Step 3: API Key (optional)
  const currentApiKey = config.get<string>("apiKey", "");
  const apiKey = await vscode.window.showInputBox({
    prompt: "Enter your API key (optional, press Enter to skip)",
    value: currentApiKey,
    placeHolder: "sk-...",
    password: true
  });

  if (apiKey !== undefined) {
    await config.update("apiKey", apiKey, vscode.ConfigurationTarget.Global);
    if (apiKey && apiKey.trim() !== "") {
      log("API key configured (hidden)");
    } else {
      log("API key cleared");
    }
  }

  // Show success message
  vscode.window.showInformationMessage(
    `CodeContinue configured successfully!\n\nEndpoint: ${endpoint}\nModel: ${model}\n\nPress Enter in a code file to get suggestions, or use Ctrl+Enter to trigger manually.`
  );

  log("Configuration wizard completed successfully");
}

/**
 * Check if this is the first run and show setup wizard
 */
function checkFirstRun(): void {
  const config = vscode.workspace.getConfiguration("codeContinue");
  const endpoint = config.get<string>("endpoint", "");

  // If endpoint is not configured, show welcome message
  if (!endpoint || endpoint.trim() === "") {
    log("First run detected, showing setup wizard");

    setTimeout(() => {
      vscode.window.showInformationMessage(
        "Welcome to CodeContinue! Configure your API endpoint to get started.",
        "Configure Now",
        "Later"
      ).then((selection) => {
        if (selection === "Configure Now") {
          vscode.commands.executeCommand("codecontinue.configure");
        } else {
          log("User postponed configuration");
          vscode.window.showInformationMessage(
            "You can configure CodeContinue anytime using the command palette: 'CodeContinue: Configure'"
          );
        }
      });
    }, 1000); // Delay to ensure extension is fully loaded
  } else {
    log(`Extension already configured with endpoint: ${endpoint}`);
  }
}

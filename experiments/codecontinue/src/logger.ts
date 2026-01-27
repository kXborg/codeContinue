import * as vscode from "vscode";

let outputChannel: vscode.OutputChannel | null = null;

/**
 * Initialize the logger output channel
 * Should be called once during extension activation
 */
export function initLogger(): void {
  if (!outputChannel) {
    outputChannel = vscode.window.createOutputChannel("CodeContinue");
  }
}

/**
 * Log a message to the output channel (if logging is enabled)
 * @param message - The message to log
 * @param level - Log level (info, warn, error)
 */
export function log(message: string, level: "info" | "warn" | "error" = "info"): void {
  const config = vscode.workspace.getConfiguration("codeContinue");
  const enableLogging = config.get<boolean>("enableLogging", false);

  if (!enableLogging && level !== "error") {
    return; // Only log errors when logging is disabled
  }

  const timestamp = new Date().toLocaleTimeString("en-US", { hour12: false });
  const levelPrefix = level === "error" ? "❌" : level === "warn" ? "⚠️" : "ℹ️";
  const logMessage = `[${timestamp}] ${levelPrefix} ${message}`;

  if (outputChannel) {
    outputChannel.appendLine(logMessage);
  }

  // Also log to console for debugging in development
  const consoleMethod = level === "error" ? console.error : level === "warn" ? console.warn : console.log;
  consoleMethod(`CodeContinue ${logMessage}`);
}

/**
 * Show the output channel (useful for debugging)
 */
export function showLog(): void {
  if (outputChannel) {
    outputChannel.show();
  }
}

/**
 * Clear the output channel
 */
export function clearLog(): void {
  if (outputChannel) {
    outputChannel.clear();
  }
}

/**
 * Dispose of the output channel
 * Should be called during extension deactivation
 */
export function disposeLogger(): void {
  if (outputChannel) {
    outputChannel.dispose();
    outputChannel = null;
  }
}

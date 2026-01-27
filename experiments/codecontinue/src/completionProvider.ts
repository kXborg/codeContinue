import * as vscode from "vscode";
import { fetchCompletion } from "./api";
import { cleanMarkdownFences, stripCommonIndent } from "./utils";
import { log } from "./logger";
import { recordRequest, isRequestStale } from "./state";

/**
 * Provides inline code completion suggestions
 */
export class CodeContinueProvider implements vscode.InlineCompletionItemProvider {

  async provideInlineCompletionItems(
    document: vscode.TextDocument,
    position: vscode.Position,
    context: vscode.InlineCompletionContext
  ): Promise<vscode.InlineCompletionItem[] | null> {

    // Only respond to automatic triggers (not manual invocations)
    if (context.triggerKind !== vscode.InlineCompletionTriggerKind.Automatic) {
      return null;
    }

    const config = vscode.workspace.getConfiguration("codeContinue");
    const maxLines = config.get<number>("maxContextLines", 40);

    // Generate unique request ID for tracking
    const requestId = `${Date.now()}-${position.line}-${position.character}`;
    recordRequest(document, requestId);

    log(`Starting completion request ${requestId} at line ${position.line}`);

    // Extract context around cursor
    const halfLines = Math.floor(maxLines / 2);
    const startLine = Math.max(0, position.line - halfLines);
    const endLine = Math.min(document.lineCount, position.line + halfLines);

    const range = new vscode.Range(
      new vscode.Position(startLine, 0),
      new vscode.Position(endLine, 0)
    );

    const contextText = document.getText(range);
    const cursorOffset = document.offsetAt(position) - document.offsetAt(range.start);

    // Build prompt with code before cursor
    const codeBefore = contextText.slice(0, cursorOffset);
    const prompt = `Continue the following code:\n${codeBefore}`;

    log(`Context: ${startLine}-${endLine} (${contextText.length} chars), cursor offset: ${cursorOffset}`);

    // Fetch completion from API
    const completion = await fetchCompletion(prompt);

    // Check if this request is still valid (not superseded by a newer one)
    if (isRequestStale(document, requestId)) {
      log(`Request ${requestId} is stale, discarding result`, "warn");
      return null;
    }

    if (!completion) {
      log(`Request ${requestId} returned no completion`);
      return null;
    }

    // Clean markdown fences and special tokens
    let cleaned = cleanMarkdownFences(completion);

    // Normalize indentation
    cleaned = stripCommonIndent(cleaned);

    log(`Request ${requestId} completed: ${cleaned.length} chars, ${cleaned.split("\n").length} lines`);

    // Return inline completion item
    return [
      new vscode.InlineCompletionItem(
        cleaned,
        new vscode.Range(position, position)
      )
    ];
  }
}

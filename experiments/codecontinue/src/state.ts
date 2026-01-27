import * as vscode from "vscode";

/**
 * State for a single document/view
 */
interface ViewState {
    /** Timestamp of the last request (milliseconds since epoch) */
    lastRequestTime: number;
    /** ID of the currently pending request (null if none) */
    pendingRequestId: string | null;
    /** Timestamp until which clearing suggestions is suppressed */
    suppressClearUntil: number;
}

/**
 * Global state storage keyed by document URI
 */
const viewStates = new Map<string, ViewState>();

/**
 * Get or create state for a document
 * @param document - The text document
 * @returns The view state for this document
 */
export function getViewState(document: vscode.TextDocument): ViewState {
    const key = document.uri.toString();

    if (!viewStates.has(key)) {
        viewStates.set(key, {
            lastRequestTime: 0,
            pendingRequestId: null,
            suppressClearUntil: 0
        });
    }

    return viewStates.get(key)!;
}

/**
 * Check if enough time has passed to make a new request (rate limiting)
 * @param document - The text document
 * @param rateLimitMs - Minimum milliseconds between requests (default from config)
 * @returns true if a new request can be made
 */
export function canMakeRequest(document: vscode.TextDocument, rateLimitMs?: number): boolean {
    const config = vscode.workspace.getConfiguration("codeContinue");
    const rateLimit = rateLimitMs ?? config.get<number>("rateLimitMs", 1000);

    const state = getViewState(document);
    const now = Date.now();
    const timeSinceLastRequest = now - state.lastRequestTime;

    return timeSinceLastRequest >= rateLimit;
}

/**
 * Record that a request has been made
 * @param document - The text document
 * @param requestId - Unique identifier for this request
 */
export function recordRequest(document: vscode.TextDocument, requestId: string): void {
    const state = getViewState(document);
    state.lastRequestTime = Date.now();
    state.pendingRequestId = requestId;
}

/**
 * Check if a request is stale (superseded by a newer request)
 * @param document - The text document
 * @param requestId - The request ID to check
 * @returns true if this request is no longer the current one
 */
export function isRequestStale(document: vscode.TextDocument, requestId: string): boolean {
    const state = getViewState(document);
    return state.pendingRequestId !== requestId;
}

/**
 * Clear the pending request ID
 * @param document - The text document
 */
export function clearRequest(document: vscode.TextDocument): void {
    const state = getViewState(document);
    state.pendingRequestId = null;
}

/**
 * Set a grace period during which suggestion clearing is suppressed
 * Useful when accepting suggestions to prevent immediate clearing
 * @param document - The text document
 * @param durationMs - Duration in milliseconds (default 200ms)
 */
export function setSuppressClearGracePeriod(document: vscode.TextDocument, durationMs: number = 200): void {
    const state = getViewState(document);
    state.suppressClearUntil = Date.now() + durationMs;
}

/**
 * Check if suggestion clearing is currently suppressed
 * @param document - The text document
 * @returns true if clearing should be suppressed
 */
export function isClearingSuppressed(document: vscode.TextDocument): boolean {
    const state = getViewState(document);
    return Date.now() < state.suppressClearUntil;
}

/**
 * Clean up state for closed documents to prevent memory leaks
 * Should be called when documents are closed
 * @param document - The text document that was closed
 */
export function cleanupDocument(document: vscode.TextDocument): void {
    const key = document.uri.toString();
    viewStates.delete(key);
}

/**
 * Get statistics about current state (for debugging)
 * @returns Object with state statistics
 */
export function getStateStats(): { totalDocuments: number; activeRequests: number } {
    let activeRequests = 0;

    for (const state of viewStates.values()) {
        if (state.pendingRequestId !== null) {
            activeRequests++;
        }
    }

    return {
        totalDocuments: viewStates.size,
        activeRequests
    };
}

/**
 * Clear all state (useful for testing or reset)
 */
export function clearAllState(): void {
    viewStates.clear();
}

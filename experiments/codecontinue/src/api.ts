import * as vscode from "vscode";
import { log } from "./logger";

/**
 * Validate that the endpoint is properly configured
 * @param endpoint - The endpoint URL to validate
 * @returns true if valid, false otherwise
 */
function isEndpointValid(endpoint: string): boolean {
  if (!endpoint || endpoint.trim() === "") {
    return false;
  }

  // Check for placeholder values
  const placeholders = ["your-api", "example.com", "localhost:0000"];
  const lowerEndpoint = endpoint.toLowerCase();

  for (const placeholder of placeholders) {
    if (lowerEndpoint.includes(placeholder)) {
      return false;
    }
  }

  // Basic URL validation
  try {
    new URL(endpoint);
    return true;
  } catch {
    return false;
  }
}

/**
 * Fetch code completion from LLM API
 * @param prompt - The prompt to send to the LLM
 * @returns The completion text, or null if failed
 */
export async function fetchCompletion(prompt: string): Promise<string | null> {
  const config = vscode.workspace.getConfiguration("codeContinue");

  const endpoint = config.get<string>("endpoint", "");
  const model = config.get<string>("model", "");
  const apiKey = config.get<string>("apiKey", "");
  const timeoutMs = config.get<number>("timeoutMs", 10000);
  const temperature = config.get<number>("temperature", 0.3);
  const maxTokens = config.get<number>("maxTokens", 1024);

  // Validate configuration
  if (!endpoint || !model) {
    vscode.window.showWarningMessage(
      "CodeContinue: Endpoint or model not configured. Run 'CodeContinue: Configure' to set up."
    );
    log("Configuration missing: endpoint or model not set", "warn");
    return null;
  }

  // Validate endpoint
  if (!isEndpointValid(endpoint)) {
    vscode.window.showWarningMessage(
      "CodeContinue: Invalid endpoint URL. Please configure a valid API endpoint."
    );
    log(`Invalid endpoint: ${endpoint}`, "warn");
    return null;
  }

  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
    log(`Request aborted after ${timeoutMs}ms timeout`, "warn");
  }, timeoutMs);

  try {
    const startTime = Date.now();
    log(`Sending request to ${endpoint} (model: ${model}, timeout: ${timeoutMs}ms)`);

    // Build headers
    const headers: Record<string, string> = {
      "Content-Type": "application/json"
    };

    // Add API key if configured
    if (apiKey && apiKey.trim() !== "") {
      headers["Authorization"] = `Bearer ${apiKey}`;
      log("Using API key for authentication");
    }

    // Build request body
    const requestBody = {
      model,
      messages: [
        {
          role: "system",
          content: "You are a code completion expert. Output ONLY the code continuation without any markdown formatting, backticks, explanations, comments, or inline comments. Write clean code without any commentary. Do NOT include any cursor markers or placeholders in your response."
        },
        {
          role: "user",
          content: prompt
        }
      ],
      temperature,
      max_tokens: maxTokens
    };

    // Make the request
    const response = await fetch(endpoint, {
      method: "POST",
      headers,
      body: JSON.stringify(requestBody),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    // Check HTTP status
    if (!response.ok) {
      const errorText = await response.text().catch(() => "Unable to read error response");
      const errorMessage = `HTTP ${response.status}: ${response.statusText}`;

      log(`API error: ${errorMessage} - ${errorText.substring(0, 200)}`, "error");

      // Provide user-friendly error messages based on status code
      if (response.status === 401) {
        vscode.window.showErrorMessage(
          "CodeContinue: Authentication failed. Check your API key."
        );
      } else if (response.status === 429) {
        vscode.window.showErrorMessage(
          "CodeContinue: Rate limit exceeded. Please wait and try again."
        );
      } else if (response.status === 500 || response.status === 502 || response.status === 503) {
        vscode.window.showErrorMessage(
          "CodeContinue: API server error. Please try again later."
        );
      } else {
        vscode.window.showErrorMessage(
          `CodeContinue: API error (${response.status}). Check logs for details.`
        );
      }

      return null;
    }

    // Parse JSON response
    let json: any;
    try {
      json = await response.json();
    } catch (parseError) {
      log(`Failed to parse JSON response: ${parseError}`, "error");
      vscode.window.showErrorMessage(
        "CodeContinue: Invalid response format from API."
      );
      return null;
    }

    const responseTime = Date.now() - startTime;

    // Extract completion from response
    const completion = json?.choices?.[0]?.message?.content ?? null;

    if (!completion) {
      log(`Empty completion received after ${responseTime}ms`, "warn");
      vscode.window.showWarningMessage(
        "CodeContinue: Received empty response from API."
      );
      return null;
    }

    // Log success
    const charCount = completion.length;
    const lineCount = completion.split("\n").length;
    log(
      `✓ Received completion in ${responseTime}ms (${charCount} chars, ${lineCount} lines)`
    );

    return completion;

  } catch (error: any) {
    clearTimeout(timeoutId);

    // Handle different error types
    if (error.name === "AbortError") {
      log(`Request timed out after ${timeoutMs}ms`, "warn");
      vscode.window.showWarningMessage(
        `CodeContinue: Request timed out. Try increasing timeout in settings (current: ${timeoutMs}ms).`
      );
    } else if (error.message?.toLowerCase().includes("fetch")) {
      log(`Network error: ${error.message}`, "error");
      vscode.window.showErrorMessage(
        "CodeContinue: Network error. Check your internet connection and endpoint URL."
      );
    } else if (error.message?.toLowerCase().includes("network")) {
      log(`Network connectivity issue: ${error.message}`, "error");
      vscode.window.showErrorMessage(
        "CodeContinue: Cannot reach API endpoint. Check your network connection."
      );
    } else {
      log(`Unexpected error: ${error.message || error}`, "error");
      vscode.window.showErrorMessage(
        `CodeContinue: ${error.message || "Unknown error occurred"}`
      );
    }

    return null;
  }
}

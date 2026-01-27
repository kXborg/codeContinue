/**
 * Remove markdown code fence markers and special tokens from LLM output
 * @param text - The text to clean
 * @returns Cleaned text
 */
export function cleanMarkdownFences(text: string): string {
    if (!text) {
        return text;
    }

    let cleaned = text;

    // Remove opening fence: ```language or just ```
    cleaned = cleaned.replace(/^\s*```[\w]*\s*\n?/g, "");

    // Remove closing fence: ```
    cleaned = cleaned.replace(/\n?\s*```\s*$/g, "");

    // Remove special tokens like [END_OF_TEXT], [INST], etc.
    cleaned = cleaned.replace(/\[END_OF_TEXT\]/g, "");
    cleaned = cleaned.replace(/\[INST\]/g, "");
    cleaned = cleaned.replace(/\[\/INST\]/g, "");
    cleaned = cleaned.replace(/<\|endoftext\|>/g, "");
    cleaned = cleaned.replace(/<\|end\|>/g, "");

    return cleaned.trim();
}

/**
 * Strip common leading whitespace from all lines
 * Useful for normalizing indentation in multi-line suggestions
 * @param text - The text to normalize
 * @returns Text with common indent removed
 */
export function stripCommonIndent(text: string): string {
    if (!text) {
        return text;
    }

    const lines = text.split("\n");

    // Find minimum indent among non-empty lines
    let minIndent = Infinity;
    for (const line of lines) {
        if (line.trim() === "") {
            continue; // Skip empty lines
        }

        const match = line.match(/^[ \t]*/);
        if (match) {
            minIndent = Math.min(minIndent, match[0].length);
        }
    }

    // If no indent found, return original
    if (minIndent === Infinity || minIndent === 0) {
        return text;
    }

    // Strip the common indent from all lines
    const normalized = lines.map(line => {
        if (line.trim() === "") {
            return line; // Keep empty lines as-is
        }
        return line.substring(minIndent);
    });

    return normalized.join("\n");
}

/**
 * Normalize indentation to match the target indent level
 * @param text - The text to normalize
 * @param targetIndent - The target indentation string (e.g., "    " for 4 spaces)
 * @returns Text with normalized indentation
 */
export function normalizeIndent(text: string, targetIndent: string = ""): string {
    // First strip common indent
    const stripped = stripCommonIndent(text);

    if (!targetIndent) {
        return stripped;
    }

    // Add target indent to each non-empty line
    const lines = stripped.split("\n");
    const normalized = lines.map(line => {
        if (line.trim() === "") {
            return line;
        }
        return targetIndent + line;
    });

    return normalized.join("\n");
}

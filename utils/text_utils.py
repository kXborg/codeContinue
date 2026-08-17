"""Pure text helpers — no Sublime imports, no I/O.

Safe to unit-test against plain inputs without a Sublime runtime.
"""

import re


# Control tokens emitted by various open-source models that should never appear
# in a code completion. Combined into a single compiled alternation so the
# response is scanned in one pass. Note: <s>/</s> (SentencePiece) are NOT
# included to avoid stripping legitimate HTML strikethrough tags in completions.
_SPECIAL_TOKEN_RE = re.compile(
    r"<\|(?:"
    r"im_start|im_end|endoftext|"
    r"begin_of_text|end_of_text|eot_id|start_header_id|end_header_id|"
    r"fim_prefix|fim_middle|fim_suffix|file_separator|"
    r"user|assistant|system"
    r")\|>"
    r"|\[(?:END_OF_TEXT|/?INST)\]"
)


def clean_markdown_fences(text):
    """Remove markdown code fence markers and model control tokens from LLM output.

    Handles:
    - Opening fence at start of string: ```python, ```
    - Closing fence at end of string: ```
    - Bracket tokens: [END_OF_TEXT], [INST], [/INST]
    - Angle-bar tokens: <|im_end|>, <|endoftext|>, Llama 3 markers, FIM markers, etc.
    """
    if not text:
        return text

    text = re.sub(r'^\s*```[\w]*\s*\n?', '', text)
    text = re.sub(r'\n?\s*```\s*$', '', text)
    text = _SPECIAL_TOKEN_RE.sub('', text)
    return text.strip()


def strip_common_indent(lines):
    """Strip the common leading indent from a list of lines.

    Returns a tuple (stripped_lines, common_prefix). The common_prefix is the
    actual whitespace that was removed (taken from the first non-empty line's
    leading run of tabs/spaces, truncated to the shortest indent length across
    all non-empty lines). Empty/whitespace-only lines are skipped when
    computing the prefix.

    The caller can re-prepend `common_prefix` to lines that need to be inserted
    at column 0 to restore their original absolute indent.
    """
    indents = []
    for ln in lines:
        if ln.strip() == "":
            continue
        m = re.match(r"^[ \t]*", ln)
        indents.append(m.group(0))
    if not indents:
        return lines, ""
    min_indent = min(len(x) for x in indents)
    common_prefix = indents[0][:min_indent]
    return [ln[min_indent:] if len(ln) >= min_indent else ln for ln in lines], common_prefix


_FUNC_PATTERNS = [
    # Python def / async def
    re.compile(r"^\s*(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)"),
    # JS/TS function
    re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s+([a-zA-Z_][a-zA-Z0-9_]*)"),
    # JS/TS const/let/var name = ...
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z_][a-zA-Z0-9_]*)\s*=>"),
    # Rust fn
    re.compile(r"^\s*(?:pub(?:\([^)]+\))?\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+([a-zA-Z_][a-zA-Z0-9_]*)"),
    # Go func
    re.compile(r"^\s*func\s+(?:\([^)]+\)\s+)?([a-zA-Z_][a-zA-Z0-9_]*)"),
    # C / C++ / Java / C#
    re.compile(r"^\s*(?:public|private|protected|static|final|native|virtual|override|inline|constexpr\s+)*(?:[a-zA-Z_][a-zA-Z0-9_<>,\[\]\s*&]+)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*(?:throws\s+[a-zA-Z0-9_,\s]+)?\s*\{?"),
]

_CLASS_PATTERNS = [
    re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?(?:public|private|protected\s+)?class\s+([a-zA-Z_][a-zA-Z0-9_]*)"),
    re.compile(r"^\s*(?:pub(?:\([^)]+\))?\s+)?struct\s+([a-zA-Z_][a-zA-Z0-9_]*)"),
    re.compile(r"^\s*(?:export\s+)?interface\s+([a-zA-Z_][a-zA-Z0-9_]*)"),
    re.compile(r"^\s*(?:pub(?:\([^)]+\))?\s+)?enum\s+([a-zA-Z_][a-zA-Z0-9_]*)"),
    re.compile(r"^\s*type\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:struct|interface)"),
]


def describe_code_selection(code, lang=""):
    """Return a short human-readable description of selected code.

    Examples:
    - '`write_text_to_file()`'
    - '`User`'
    - '12 lines of code'
    """
    if not code or not code.strip():
        return "selected code"

    lines = [ln for ln in code.splitlines() if ln.strip()]
    if not lines:
        return "selected code"

    for line in lines[:5]:
        for pat in _CLASS_PATTERNS:
            m = pat.match(line)
            if m:
                return "`{0}`".format(m.group(1))
        for pat in _FUNC_PATTERNS:
            m = pat.match(line)
            if m:
                return "`{0}()`".format(m.group(1))

    n = len(lines)
    if n == 1:
        return "1 line of code"
    return "{0} lines of code".format(n)


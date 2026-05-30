"""Tests for utils.text_utils — pure text helpers."""

import unittest
import sys
import os

# Allow importing from the package root without installing.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.text_utils import clean_markdown_fences, strip_common_indent


class TestCleanMarkdownFences(unittest.TestCase):
    """clean_markdown_fences should strip fences and model control tokens."""

    # --- Fence removal ---

    def test_opening_fence_with_language(self):
        text = "```python\nprint('hello')\n```"
        self.assertEqual(clean_markdown_fences(text), "print('hello')")

    def test_opening_fence_without_language(self):
        text = "```\nreturn 42\n```"
        self.assertEqual(clean_markdown_fences(text), "return 42")

    def test_no_fences(self):
        text = "x = 1\ny = 2"
        self.assertEqual(clean_markdown_fences(text), "x = 1\ny = 2")

    def test_empty_string(self):
        self.assertEqual(clean_markdown_fences(""), "")

    def test_none_passthrough(self):
        self.assertIsNone(clean_markdown_fences(None))

    def test_only_fences(self):
        text = "```python\n```"
        self.assertEqual(clean_markdown_fences(text), "")

    def test_fence_with_trailing_whitespace(self):
        text = "```  \ncode()\n```  "
        self.assertEqual(clean_markdown_fences(text), "code()")

    # --- Control token removal ---

    def test_im_end_token(self):
        text = "result = 42<|im_end|>"
        self.assertEqual(clean_markdown_fences(text), "result = 42")

    def test_im_start_token(self):
        text = "<|im_start|>code here"
        self.assertEqual(clean_markdown_fences(text), "code here")

    def test_endoftext_token(self):
        text = "return x<|endoftext|>"
        self.assertEqual(clean_markdown_fences(text), "return x")

    def test_llama3_tokens(self):
        text = "<|begin_of_text|>code<|end_of_text|>"
        self.assertEqual(clean_markdown_fences(text), "code")

    def test_llama3_header_tokens(self):
        text = "<|start_header_id|>assistant<|end_header_id|>code"
        self.assertEqual(clean_markdown_fences(text), "assistantcode")

    def test_eot_id_token(self):
        text = "x = 1<|eot_id|>"
        self.assertEqual(clean_markdown_fences(text), "x = 1")

    def test_fim_tokens(self):
        text = "<|fim_prefix|>before<|fim_middle|>after<|fim_suffix|>"
        self.assertEqual(clean_markdown_fences(text), "beforeafter")

    def test_file_separator_token(self):
        text = "code<|file_separator|>more"
        self.assertEqual(clean_markdown_fences(text), "codemore")

    def test_role_tokens(self):
        for role in ["user", "assistant", "system"]:
            text = "<|{0}|>content".format(role)
            self.assertEqual(clean_markdown_fences(text), "content", msg=role)

    def test_bracket_end_of_text(self):
        text = "return 1[END_OF_TEXT]"
        self.assertEqual(clean_markdown_fences(text), "return 1")

    def test_bracket_inst_tokens(self):
        text = "[INST]question[/INST]answer"
        self.assertEqual(clean_markdown_fences(text), "questionanswer")

    def test_multiple_tokens_in_one_string(self):
        text = "```python\nresult<|im_end|><|endoftext|>\n```"
        self.assertEqual(clean_markdown_fences(text), "result")

    # --- Edge cases ---

    def test_fence_in_middle_not_stripped(self):
        """Only fences at the very start/end should be removed."""
        text = "line1\n```\nline3"
        result = clean_markdown_fences(text)
        # The opening regex is anchored to ^ so mid-text ``` stays.
        self.assertIn("```", result)

    def test_preserves_html_angle_brackets(self):
        """Normal < > should not be stripped (only <|...|> control tokens)."""
        text = "if (x < 10 && y > 5) {}"
        self.assertEqual(clean_markdown_fences(text), "if (x < 10 && y > 5) {}")


class TestStripCommonIndent(unittest.TestCase):
    """strip_common_indent should remove the shared leading whitespace."""

    def test_uniform_indent(self):
        lines = ["    a", "    b", "    c"]
        stripped, prefix = strip_common_indent(lines)
        self.assertEqual(stripped, ["a", "b", "c"])
        self.assertEqual(prefix, "    ")

    def test_mixed_indent_depth(self):
        lines = ["    a", "        b", "    c"]
        stripped, prefix = strip_common_indent(lines)
        self.assertEqual(stripped, ["a", "    b", "c"])
        self.assertEqual(prefix, "    ")

    def test_no_indent(self):
        lines = ["a", "b"]
        stripped, prefix = strip_common_indent(lines)
        self.assertEqual(stripped, ["a", "b"])
        self.assertEqual(prefix, "")

    def test_single_line(self):
        lines = ["  hello"]
        stripped, prefix = strip_common_indent(lines)
        self.assertEqual(stripped, ["hello"])
        self.assertEqual(prefix, "  ")

    def test_empty_lines_ignored(self):
        lines = ["    a", "", "    b"]
        stripped, prefix = strip_common_indent(lines)
        self.assertEqual(prefix, "    ")
        # The empty line stays as-is (length < min_indent).
        self.assertEqual(stripped[0], "a")
        self.assertEqual(stripped[2], "b")

    def test_whitespace_only_lines_ignored(self):
        lines = ["    a", "   ", "    b"]
        stripped, prefix = strip_common_indent(lines)
        self.assertEqual(prefix, "    ")

    def test_all_empty(self):
        lines = ["", "", ""]
        stripped, prefix = strip_common_indent(lines)
        self.assertEqual(prefix, "")
        self.assertEqual(stripped, ["", "", ""])

    def test_tabs(self):
        lines = ["\ta", "\tb"]
        stripped, prefix = strip_common_indent(lines)
        self.assertEqual(stripped, ["a", "b"])
        self.assertEqual(prefix, "\t")

    def test_mixed_tabs_and_spaces(self):
        lines = ["\t a", "\t b"]
        stripped, prefix = strip_common_indent(lines)
        self.assertEqual(stripped, ["a", "b"])
        self.assertEqual(prefix, "\t ")

    def test_returns_original_lines_when_no_common_indent(self):
        lines = ["a", "  b"]
        stripped, prefix = strip_common_indent(lines)
        self.assertEqual(stripped, ["a", "  b"])
        self.assertEqual(prefix, "")


if __name__ == "__main__":
    unittest.main()

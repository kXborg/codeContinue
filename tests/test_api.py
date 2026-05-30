"""Tests for utils.api — HTTP / auth helpers."""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.api import build_api_headers


class TestBuildApiHeaders(unittest.TestCase):
    """build_api_headers should set Content-Type and conditionally Authorization."""

    def test_with_api_key(self):
        settings = {"api_key": "sk-abc123"}
        headers = build_api_headers(settings)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Authorization"], "Bearer sk-abc123")

    def test_without_api_key(self):
        settings = {"api_key": ""}
        headers = build_api_headers(settings)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertNotIn("Authorization", headers)

    def test_missing_api_key(self):
        """When api_key is not present at all, no Authorization header."""
        settings = {}
        headers = build_api_headers(settings)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertNotIn("Authorization", headers)

    def test_api_key_is_none(self):
        """A falsy api_key should not produce an Authorization header."""
        settings = {"api_key": None}
        headers = build_api_headers(settings)
        self.assertNotIn("Authorization", headers)

    def test_api_key_whitespace_only(self):
        """Whitespace-only keys are truthy strings — header IS produced.

        The server will reject it, but that's the correct behaviour: we
        forward whatever the user configured.
        """
        settings = {"api_key": "   "}
        headers = build_api_headers(settings)
        self.assertIn("Authorization", headers)

    def test_huggingface_style_key(self):
        settings = {"api_key": "hf_aBcDeFgHiJkLmNoP"}
        headers = build_api_headers(settings)
        self.assertEqual(headers["Authorization"], "Bearer hf_aBcDeFgHiJkLmNoP")


if __name__ == "__main__":
    unittest.main()

"""HTTP / auth helpers for talking to OpenAI-compatible chat endpoints.

`settings` is duck-typed (anything with `.get(key, default)`), so callers can
pass either a `sublime.Settings` object or a plain dict in tests.
"""


def build_api_headers(settings):
    """Build request headers including Authorization if api_key is set."""
    headers = {"Content-Type": "application/json"}
    api_key = settings.get("api_key", "")
    if api_key:
        headers["Authorization"] = "Bearer {0}".format(api_key)
    return headers

"""HTTP / auth helpers for talking to OpenAI-compatible chat endpoints.

`settings` is duck-typed (anything with `.get(key, default)`), so callers can
pass either a `sublime.Settings` object or a plain dict in tests.
"""


class OpenAIProvider:
    def build_headers(self, settings):
        headers = {"Content-Type": "application/json"}
        api_key = settings.get("api_key", "")
        if api_key:
            headers["Authorization"] = "Bearer {0}".format(api_key)
        return headers

    def format_payload(self, model, messages, max_tokens, temperature, stream=False):
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        if stream:
            payload["stream"] = True
        return payload

    def parse_response(self, result_dict):
        return result_dict.get("choices", [{}])[0].get("message", {}).get("content", "").strip()


class AnthropicProvider:
    def build_headers(self, settings):
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        api_key = settings.get("api_key", "")
        if api_key:
            headers["x-api-key"] = api_key
        return headers

    def format_payload(self, model, messages, max_tokens, temperature, stream=False):
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        if stream:
            payload["stream"] = True

        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                payload["system"] = msg["content"]
            else:
                anthropic_messages.append(msg)
                
        payload["messages"] = anthropic_messages
        return payload

    def parse_response(self, result_dict):
        content = result_dict.get("content", [])
        if content and len(content) > 0:
            return content[0].get("text", "").strip()
        return ""


def get_provider(endpoint, settings=None):
    """Return the appropriate API provider for the endpoint."""
    if settings:
        provider_name = settings.get("provider", "").lower()
        if provider_name == "anthropic":
            return AnthropicProvider()
        elif provider_name == "openai":
            return OpenAIProvider()

    if "api.anthropic.com" in endpoint or "/v1/messages" in endpoint:
        return AnthropicProvider()
    
    return OpenAIProvider()


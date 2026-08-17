"""HTTP / auth helpers for talking to OpenAI-compatible chat endpoints.

`settings` is duck-typed (anything with `.get(key, default)`), so callers can
pass either a `sublime.Settings` object or a plain dict in tests.
"""


class OpenAIProvider:
    def build_headers(self, settings):
        headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
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
            "User-Agent": "Mozilla/5.0",
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


import json
import urllib.error
import urllib.request


def normalize_endpoint(url):
    """Normalize a base host or partial URL to a full completions/messages endpoint.

    Examples:
    - 'http://192.168.1.6:1234' -> 'http://192.168.1.6:1234/v1/chat/completions'
    - 'http://192.168.1.6:1234/v1' -> 'http://192.168.1.6:1234/v1/chat/completions'
    - 'http://192.168.1.6:1234/v1/chat/completions' -> 'http://192.168.1.6:1234/v1/chat/completions'
    - 'https://api.anthropic.com' -> 'https://api.anthropic.com/v1/messages'
    - 'http://localhost:11434/api/chat' -> 'http://localhost:11434/api/chat'
    """
    if not url:
        return ""
    url = url.strip().rstrip("/")
    if not url:
        return ""

    if url.endswith(("/chat/completions", "/messages", "/generate", "/api/chat")):
        return url

    if "anthropic.com" in url:
        if url.endswith("/v1"):
            return "{0}/messages".format(url)
        return "{0}/v1/messages".format(url)

    if url.endswith("/v1"):
        return "{0}/chat/completions".format(url)

    return "{0}/v1/chat/completions".format(url)


def get_models_endpoint(endpoint):
    """Derive the models list endpoint from a chat/messages endpoint."""
    endpoint = normalize_endpoint(endpoint)
    if not endpoint:
        return ""

    if "/v1/chat/completions" in endpoint:
        return endpoint.replace("/v1/chat/completions", "/v1/models")
    if "/chat/completions" in endpoint:
        return endpoint.replace("/chat/completions", "/models")
    if "/v1/messages" in endpoint:
        return endpoint.replace("/v1/messages", "/v1/models")
    if "/api/chat" in endpoint:
        return endpoint.replace("/api/chat", "/api/tags")

    return endpoint.rstrip("/") + "/models"


def fetch_models(endpoint, api_key="", timeout_s=3.0):
    """Fetch available model IDs from the endpoint (e.g. /v1/models).

    Returns a list of model ID strings, or empty list on failure.
    """
    models_url = get_models_endpoint(endpoint)
    if not models_url:
        return []

    headers = {"User-Agent": "Mozilla/5.0"}
    if api_key:
        if "anthropic" in endpoint.lower():
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = "Bearer {0}".format(api_key)

    req = urllib.request.Request(models_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read().decode())
            # OpenAI / LM Studio / vLLM: {"data": [{"id": "model_id"}, ...]}
            if "data" in data and isinstance(data["data"], list):
                models = []
                for item in data["data"]:
                    if isinstance(item, dict) and "id" in item:
                        models.append(str(item["id"]))
                    elif isinstance(item, str):
                        models.append(item)
                return models
            # Ollama: {"models": [{"name": "model_id"}, ...]}
            if "models" in data and isinstance(data["models"], list):
                models = []
                for item in data["models"]:
                    if isinstance(item, dict) and "name" in item:
                        models.append(str(item["name"]))
                    elif isinstance(item, str):
                        models.append(item)
                return models
    except Exception:
        pass

    return []


def test_endpoint_connectivity(endpoint, api_key="", timeout_s=3.0):
    """Test if the endpoint server is reachable.

    Returns (is_ok: bool, message: str).
    """
    if not endpoint:
        return False, "No endpoint provided."

    norm_url = normalize_endpoint(endpoint)
    models_url = get_models_endpoint(norm_url)

    headers = {"User-Agent": "Mozilla/5.0"}
    if api_key:
        headers["Authorization"] = "Bearer {0}".format(api_key)

    try:
        req = urllib.request.Request(models_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout_s):
            return True, "Connected successfully"
    except urllib.error.HTTPError as e:
        # HTTP status code (401, 403, 404, 405) means server is reachable
        if e.code in (400, 401, 403, 404, 405):
            return True, "Server reachable (HTTP {0})".format(e.code)
        return False, "Server returned HTTP {0}: {1}".format(e.code, str(e.reason)[:60])
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if "refused" in reason.lower():
            return False, "Connection refused. Is your local LLM server running?"
        if "timed out" in reason.lower():
            return False, "Connection timed out. Check IP/port or firewall."
        return False, "Network error: {0}".format(reason[:60])
    except Exception as e:
        return False, "Connection error: {0}".format(str(e)[:60])



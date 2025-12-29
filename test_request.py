import json
import time
import urllib.request

endpoint = "https://deplorably-athonite-loreta.ngrok-free.dev/v1/chat/completions"
headers = {"Content-Type": "application/json"}

data = {
    "model": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
    "messages": [
        {"role": "system", "content": "You are a code completion assistant. Only return code."},
        {"role": "user", "content": "print('hello')<cursor>"}
    ],
    "max_tokens": 10,
    "temperature": 0.0
}

req = urllib.request.Request(endpoint, data=json.dumps(data).encode(), headers=headers)
try:
    start = time.time()
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode()
    duration = (time.time() - start) * 1000.0
    print(f"TimeMs:{duration:.0f}")
    print(body)
except Exception as e:
    print("ERROR:", str(e))

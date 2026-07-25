import json
import sys

import requests

import config

BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Выполняет bash-команду в системном терминале. Возвращает stdout и stderr.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Bash-команда для выполнения",
                }
            },
            "required": ["command"],
        },
    },
}


class OpenRouterClient:
    def __init__(self):
        self.api_key = config.API_KEY
        self.model = config.MODEL
        self.base_url = config.BASE_URL
        self.max_context = self._fetch_max_context()

    def _fetch_max_context(self):
        try:
            resp = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
            resp.raise_for_status()
            for m in resp.json().get("data", []):
                if m.get("id") == self.model:
                    return m.get("context_length")
        except KeyboardInterrupt:
            raise
        except Exception:
            pass
        return None

    def chat(self, messages, tools=None, stream=True):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/mini-agent",
            "X-Title": "mini-agent",
        }

        body = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            body["tools"] = tools

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body,
                stream=stream,
                timeout=120,
            )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError:
            print("\nОшибка: не удалось подключиться к OpenRouter")
            return None
        except requests.exceptions.Timeout:
            print("\nОшибка: таймаут запроса")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"\nОшибка API: {e}")
            try:
                print(resp.json())
            except Exception:
                print(resp.text[:500])
            return None

        resp.encoding = "utf-8"

        if stream:
            return self._parse_stream(resp)
        else:
            return resp.json()["choices"][0]["message"]

    def _parse_stream(self, resp):
        content_parts = []
        tool_calls = {}
        finish_reason = None
        usage = None

        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data = line[6:]
            if data.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue

            choice = chunk.get("choices", [{}])[0]
            delta = choice.get("delta", {})
            fr = choice.get("finish_reason")
            if fr:
                finish_reason = fr

            if chunk.get("usage"):
                usage = chunk["usage"]

            if delta.get("content"):
                text = delta["content"]
                content_parts.append(text)
                print(text, end="", flush=True)

            for tc in delta.get("tool_calls", []):
                idx = tc.get("index", 0)
                if idx not in tool_calls:
                    tool_calls[idx] = {
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    }
                if tc.get("id"):
                    tool_calls[idx]["id"] = tc["id"]
                if tc.get("function", {}).get("name"):
                    tool_calls[idx]["function"]["name"] = tc["function"]["name"]
                if tc.get("function", {}).get("arguments"):
                    tool_calls[idx]["function"]["arguments"] += tc["function"]["arguments"]

        if content_parts:
            print()

        message = {"role": "assistant", "content": "".join(content_parts) or None}

        if tool_calls:
            message["tool_calls"] = [tool_calls[i] for i in sorted(tool_calls.keys())]

        if finish_reason:
            message["finish_reason"] = finish_reason

        return message, usage

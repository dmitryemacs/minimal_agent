import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

import config
from api import OpenRouterClient, BASH_TOOL
from tools import execute_bash

SESSIONS_DIR = Path.home() / ".config" / "mini-agent" / "sessions"


def ensure_sessions_dir():
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_session(session_id, messages):
    ensure_sessions_dir()
    path = SESSIONS_DIR / f"{session_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def list_sessions():
    ensure_sessions_dir()
    sessions = []
    for p in sorted(SESSIONS_DIR.glob("*.json"), reverse=True):
        try:
            with open(p, encoding="utf-8") as f:
                msgs = json.load(f)
            user_msgs = [m for m in msgs if m.get("role") == "user"]
            first = user_msgs[0]["content"][:60] if user_msgs else "(пусто)"
            sessions.append((p.stem, len(user_msgs), first))
        except Exception:
            continue
    return sessions


def load_session(session_id):
    path = SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Agent:
    def __init__(self, session_id=None, messages=None):
        self.client = OpenRouterClient()
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.messages = messages or [{"role": "system", "content": config.SYSTEM_PROMPT}]
        self.auto_confirm = False
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0

    def handle_tool_calls(self, tool_calls):
        results = []
        for tc in tool_calls:
            func_name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                args = {}

            if func_name == "bash":
                command = args.get("command", "")
                result = execute_bash(command, auto_confirm=self.auto_confirm)
            else:
                result = f"Неизвестный инструмент: {func_name}"

            print(f"\n\033[36m{result}\033[0m")
            results.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })
        return results

    def run(self):
        ctx = self.client.max_context
        ctx_str = f" | контекст: {ctx:,}" if ctx else ""
        print(f"mini-agent | модель: {self.client.model}{ctx_str} | сессия: {self.session_id}")
        print("Команды: /exit, /clear, /history, /sessions, /new\n")

        while True:
            try:
                user_input = input("\033[32mmini-agent>\033[0m ").strip()
            except (EOFError, KeyboardInterrupt):
                save_session(self.session_id, self.messages)
                print("\nСессия сохранена. Выход.")
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                self.handle_command(user_input)
                continue

            self.messages.append({"role": "user", "content": user_input})

            while True:
                response, usage = self.client.chat(
                    self.messages, tools=[BASH_TOOL], stream=True
                )
                if response is None:
                    print("Нет ответа от модели. Попробуйте снова.")
                    self.messages.pop()
                    break

                if usage:
                    self.total_prompt_tokens += usage.get("prompt_tokens", 0)
                    self.total_completion_tokens += usage.get("completion_tokens", 0)
                    self.total_tokens += usage.get("total_tokens", 0)
                    ctx = self.client.max_context
                    used = usage.get("prompt_tokens", 0)
                    pct = f" ({used * 100 // ctx}% of {ctx:,})" if ctx else ""
                    print(f"\033[90m[tokens: {used} in / {usage.get('completion_tokens', 0)} out | total: {self.total_tokens}{pct}]\033[0m")

                self.messages.append(response)

                if response.get("tool_calls"):
                    results = self.handle_tool_calls(response["tool_calls"])
                    self.messages.extend(results)
                else:
                    break

            save_session(self.session_id, self.messages)

    def handle_command(self, cmd):
        cmd = cmd.lower()
        if cmd == "/exit":
            save_session(self.session_id, self.messages)
            print("Сессия сохранена. Выход.")
            sys.exit(0)
        elif cmd == "/clear":
            self.messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            print(f"История очищена. Новая сессия: {self.session_id}")
        elif cmd == "/history":
            shown = False
            for msg in self.messages:
                role = msg["role"]
                if role == "system":
                    continue
                content = msg.get("content") or ""
                if content:
                    shown = True
                    preview = content[:100].replace("\n", " ")
                    print(f"  [{role}] {preview}")
            if not shown:
                print("  (пусто)")
        elif cmd == "/sessions":
            sessions = list_sessions()
            if not sessions:
                print("  Нет сохранённых сессий.")
            else:
                print("  Сохранённые сессии:")
                for sid, count, preview in sessions:
                    marker = " <- текущая" if sid == self.session_id else ""
                    print(f"    {sid} ({count} сообщ.) — {preview}{marker}")
        elif cmd.startswith("/resume"):
            parts = cmd.split(maxsplit=1)
            if len(parts) < 2:
                sessions = list_sessions()
                if not sessions:
                    print("  Нет сессий для восстановления.")
                    return
                print("  Используйте /resume ID")
                for sid, count, preview in sessions[:5]:
                    print(f"    {sid} — {preview[:40]}")
                return
            sid = parts[1]
            msgs = load_session(sid)
            if msgs is None:
                print(f"  Сессия {sid} не найдена.")
                return
            self.session_id = sid
            self.messages = msgs
            print(f"  Сессия {sid} восстановлена ({len(msgs)} сообщений).")
        elif cmd == "/new":
            save_session(self.session_id, self.messages)
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]
            print(f"Новая сессия: {self.session_id}")
        elif cmd == "/auto":
            self.auto_confirm = not self.auto_confirm
            state = "вкл" if self.auto_confirm else "выкл"
            print(f"Авто-подтверждение: {state}")
        else:
            print(f"Неизвестная команда: {cmd}")


if __name__ == "__main__":
    Agent().run()

import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

import config
from api import OpenRouterClient, BASH_TOOL
from tools import execute_bash


class Agent:
    def __init__(self):
        self.client = OpenRouterClient()
        self.messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]
        self.auto_confirm = False

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
        print(f"mini-agent | модель: {self.client.model}")
        print("Команды: /exit, /clear, /history\n")

        while True:
            try:
                user_input = input("\033[32mmini-agent>\033[0m ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nВыход.")
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                self.handle_command(user_input)
                continue

            self.messages.append({"role": "user", "content": user_input})

            while True:
                response = self.client.chat(
                    self.messages, tools=[BASH_TOOL], stream=True
                )
                if response is None:
                    print("Нет ответа от модели. Попробуйте снова.")
                    self.messages.pop()
                    break

                self.messages.append(response)

                if response.get("tool_calls"):
                    results = self.handle_tool_calls(response["tool_calls"])
                    self.messages.extend(results)
                else:
                    break

    def handle_command(self, cmd):
        cmd = cmd.lower()
        if cmd == "/exit":
            print("Выход.")
            sys.exit(0)
        elif cmd == "/clear":
            self.messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]
            print("История очищена.")
        elif cmd == "/history":
            for msg in self.messages:
                role = msg["role"]
                if role == "system":
                    continue
                content = msg.get("content", "")
                if content:
                    preview = content[:100].replace("\n", " ")
                    print(f"  [{role}] {preview}")
        elif cmd == "/auto":
            self.auto_confirm = not self.auto_confirm
            state = "вкл" if self.auto_confirm else "выкл"
            print(f"Авто-подтверждение: {state}")
        else:
            print(f"Неизвестная команда: {cmd}")


if __name__ == "__main__":
    Agent().run()

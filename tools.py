import subprocess
import sys


def get_shell():
    if sys.platform == "win32":
        return "cmd"
    return "bash"


def confirm_command(command):
    print(f"\n\033[33m⚡ Команда: {command}\033[0m")
    print("[y] да  [n] нет  [a] да для всех")
    answer = input("Выполнить? ").strip().lower()
    return answer in ("y", "a"), answer == "a"


def execute_bash(command, auto_confirm=False):
    if not auto_confirm:
        allowed, trust_all = confirm_command(command)
        if not allowed:
            return "Команда отменена пользователем"
        auto_confirm = trust_all

    shell = get_shell()
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
            executable=None if shell == "cmd" else "/bin/bash",
            env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8", "LANG": "en_US.UTF-8"},
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"
        return output.strip() or "(нет вывода)"
    except subprocess.TimeoutExpired:
        return "Ошибка: команда выполнялась дольше 120 секунд и была прервана"
    except Exception as e:
        return f"Ошибка выполнения: {e}"

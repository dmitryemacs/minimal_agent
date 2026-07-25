import os
import sys
from pathlib import Path


def load_dotenv():
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key not in os.environ:
                os.environ[key] = value


load_dotenv()

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL = os.environ.get("MODEL", "anthropic/claude-sonnet-4")
BASE_URL = os.environ.get("BASE_URL", "https://openrouter.ai/api/v1")

if not API_KEY:
    print("Ошибка: не задан OPENROUTER_API_KEY")
    print("Установите переменную окружения или создайте .env файл")
    sys.exit(1)

SYSTEM_PROMPT = """Ты — AI-агент с доступом к bash-командам.

Тебе доступен инструмент bash для выполнения команд в терминале.
Используй его когда нужно выполнить системную команду, проверить файлы, установить пакеты и т.д.

Правила:
- Выполняй только те команды, которые реально необходимы для решения задачи
- Не выполняй опасные команды без веской причины (rm -rf /, форматирование дисков и т.д.)
- Объясняй что делаешь перед вызовом инструмента
- Если команда вернула ошибку, попробуй исправить и повторить
- Будь лаконичен в ответах"""

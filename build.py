#!/usr/bin/env python3
"""Скрипт сборки mini-agent в один бинарник."""
import subprocess
import sys
import shutil
from pathlib import Path


def build():
    dist = Path("dist")
    build = Path("build")
    if dist.exists():
        shutil.rmtree(dist)
    if build.exists():
        shutil.rmtree(build)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "mini-agent",
        "--clean",
        "--noconfirm",
        "--hidden-import", "config",
        "--hidden-import", "api",
        "--hidden-import", "tools",
        "--hidden-import", "requests",
        "agent.py",
    ]

    print("Сборка mini-agent...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("Ошибка сборки!")
        sys.exit(1)

    binary = dist / "mini-agent"
    if sys.platform == "win32":
        binary = dist / "mini-agent.exe"

    if binary.exists():
        size_mb = binary.stat().st_size / (1024 * 1024)
        print(f"\nГотово: {binary} ({size_mb:.1f} MB)")
    else:
        print("Бинарник не найден в dist/")
        sys.exit(1)


if __name__ == "__main__":
    build()

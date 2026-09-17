"""Runs every test_* function across tests/test_*.py modules.

Usage: python -m tests.run_all
"""
import asyncio
import importlib
import inspect
import pkgutil
from pathlib import Path


def _iter_test_modules():
    package_dir = Path(__file__).parent
    for module_info in sorted(pkgutil.iter_modules([str(package_dir)]), key=lambda m: m.name):
        if module_info.name.startswith("test_"):
            yield importlib.import_module(f"tests.{module_info.name}")


def main() -> None:
    for module in _iter_test_modules():
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            if inspect.iscoroutinefunction(func):
                asyncio.run(func())
            else:
                func()
    print("Все проверки пройдены")


if __name__ == "__main__":
    main()

"""Throwaway playground for comparing table-rendering styles.

Nothing outside this package imports from it except three wiring lines tagged
"# sandbox" (texts.py, keyboards.py, handlers/__init__.py). Deleting the directory
and reverting those three lines removes the feature entirely.

Only sandbox/handlers.py knows about aiogram; everything else is pure str -> str,
so every style is testable without a live bot.

TableData lives in views.py now (it is production's envelope for stats data), so the
sandbox depends on production instead of the other way around -- this is the one
line that keeps the two definitions from drifting apart.
"""
from views import TableData

__all__ = ["TableData"]

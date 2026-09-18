"""Throwaway playground for comparing table-rendering styles.

Nothing outside this package imports from it except three wiring lines tagged
"# sandbox" (texts.py, keyboards.py, handlers/__init__.py). Deleting the directory
and reverting those three lines removes the feature entirely.

Only sandbox/handlers.py knows about aiogram; everything else is pure str -> str,
so every style is testable without a live bot.
"""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TableData:
    """Everything a renderer is allowed to see, in one frozen envelope.

    Field order mirrors utils.create_stats_text(start, end, total_e, expense, income,
    total_i) so the baseline variant is a one-line splat and graduating a winner back
    into utils.py stays mechanical.

    expense/income rows are index-by-name mappings. aiosqlite.Row and plain dict both
    satisfy that, which is why hardcoded fixtures and real DB rows are interchangeable
    here without any adapter layer.
    """

    start: str
    end: str
    total_e: int
    expense: Sequence[Mapping]
    income: Sequence[Mapping]
    total_i: int

    @property
    def diff(self) -> int:
        return self.total_i - self.total_e

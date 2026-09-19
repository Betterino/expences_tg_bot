"""Display helpers for the sandbox's HTML-based table variants.

visible()/fit()/format_money() graduated to utils.py (Step 1) since production code
(handlers/edit.py, views.py) needs them too. This module keeps only the padding
helpers that exist purely to lay out monospace columns by hand -- rich blocks
(richtext.py) let Telegram do that instead, so nothing here is needed once a variant
moves off <pre>/<code>.
"""
from utils import fit, format_money, visible

money = format_money  # sandbox alias kept for the HTML variants that pass sep=SEP


def width(text: str) -> int:
    return len(visible(text))


def rpad(text: str, limit: int, filler: str = " ") -> str:
    """Left-align in `limit` columns. filler="." gives dot leaders."""
    cut = fit(text, limit)
    return cut + filler * max(0, limit - width(cut))


def lpad(text: str, limit: int, filler: str = " ") -> str:
    """Right-align in `limit` columns -- what numbers want."""
    cut = fit(text, limit)
    return filler * max(0, limit - width(cut)) + cut


def bar(total: int, maximum: int, cells: int = 10, full: str = "█", empty: str = "░") -> str:
    """Progress bar, or "" when the category has no maximum set."""
    if maximum <= 0:
        return ""
    filled = min(round(total / maximum * cells), cells)
    return full * filled + empty * (cells - filled)


def percent(total: int, maximum: int) -> str:
    return "" if maximum <= 0 else f"{round(total / maximum * 100)}%"

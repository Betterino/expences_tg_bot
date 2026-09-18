"""Display helpers: measure and cut text by *visible* columns, not by len().

Why this file exists at all: category names and nicknames are html.escape()d at INPUT
time (handlers/edit.py:146, handlers/settings.py:91) and stored escaped in SQLite. So
"Кафе & бары" lives in the DB as "Кафе &amp; бары" -- 15 characters in Python, 11
columns on screen. Today's create_stats_text() pads with f-string widths ({name:<18}),
which counts the 15, so any category containing & < > or " silently shifts its row's
columns out of alignment. Every helper below measures on the unescaped form and
escapes exactly once on the way out.
"""
import html

from utils import format_money

ELLIPSIS = "…"


def visible(text: str) -> str:
    """The form the user actually sees -- what we measure and slice against."""
    return html.unescape(str(text))


def width(text: str) -> int:
    return len(visible(text))


def fit(text: str, limit: int) -> str:
    """Truncate to `limit` visible columns and return HTML-safe output.

    Cutting happens before re-escaping, so an entity can never be split in half the
    way handlers/edit.py:150 can today (it truncates *after* escaping, which can leave
    a dangling "&am").
    """
    raw = visible(text)
    if len(raw) <= limit:
        return html.escape(raw, quote=False)
    if limit <= 0:
        return ""
    return html.escape(raw[: limit - 1], quote=False) + ELLIPSIS


def rpad(text: str, limit: int, filler: str = " ") -> str:
    """Left-align in `limit` columns. filler="." gives dot leaders."""
    cut = fit(text, limit)
    return cut + filler * max(0, limit - width(cut))


def lpad(text: str, limit: int, filler: str = " ") -> str:
    """Right-align in `limit` columns -- what numbers want."""
    cut = fit(text, limit)
    return filler * max(0, limit - width(cut)) + cut


def money(value: int, sep: str = "") -> str:
    """utils.format_money stays the source of truth for kopeks; sep adds grouping.

    The abs()/sign dance is not cosmetic: format_money(-1205) returns "-13,95" because
    Python floors -1205 // 100 to -13 and -1205 % 100 to 95. That reaches the user
    today on the "Итого" line whenever the month runs a deficit with kopeks in it.
    """
    sign = "-" if value < 0 else ""
    text = format_money(abs(value))
    if not sep:
        return sign + text
    rub, _, kop = text.partition(",")
    grouped = f"{int(rub):,}".replace(",", sep)
    return f"{sign}{grouped},{kop}" if kop else sign + grouped


def bar(total: int, maximum: int, cells: int = 10, full: str = "█", empty: str = "░") -> str:
    """Progress bar, or "" when the category has no maximum set."""
    if maximum <= 0:
        return ""
    filled = min(round(total / maximum * cells), cells)
    return full * filled + empty * (cells - filled)


def percent(total: int, maximum: int) -> str:
    return "" if maximum <= 0 else f"{round(total / maximum * 100)}%"

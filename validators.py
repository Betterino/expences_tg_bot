"""Boundary validation for untrusted CallbackData fields.

Every CallbackData field is a free str/int that a client can set to anything --
Telegram never checks the bytes came from a button we actually rendered (see
tests/test_security.py for the same threat model against category ids). The domains
here are read off the same tables the keyboards already use (HISTORY_CYCLES, MONTHS,
TIMEZONES) instead of duplicating them, so a new timezone or history filter can't
silently desync validation from what's actually offered.
"""
from constants import ADD_MODES, HISTORY_CYCLES, KINDS, TIMEZONES
from texts import MONTHS


def normalize_history(kind: str | None, who: str, sort: str) -> tuple[str | None, str, str]:
    """Crafted HistoryPageCB fields fall back to the "show everything" defaults
    instead of KeyError-ing keyboards.history_kb / views.history_view."""
    if kind not in HISTORY_CYCLES["kind"]:
        kind = None
    if who not in HISTORY_CYCLES["who"]:
        who = "all"
    if sort not in HISTORY_CYCLES["sort"]:
        sort = "id"
    return kind, who, sort


def clamp_month_index(month: int) -> int | None:
    """MonthCB.month indexes MONTHS (0-11); None means "reject with a toast"."""
    if not isinstance(month, int) or isinstance(month, bool) or not (0 <= month < len(MONTHS)):
        return None
    return month


def clamp_stats_month(month: int) -> int | None:
    """StatsCB.month is a real calendar month (1-12), unlike MonthCB's 0-based index."""
    if not isinstance(month, int) or isinstance(month, bool) or not (1 <= month <= 12):
        return None
    return month


def clamp_year(year: int) -> int | None:
    if not isinstance(year, int) or isinstance(year, bool) or not (1970 <= year <= 2100):
        return None
    return year


def tz_index(index: int) -> int | None:
    """TzCB.index into TIMEZONES -- reject negative (Python wraps and silently picks
    the wrong zone) and out-of-range instead of indexing blind."""
    if not isinstance(index, int) or isinstance(index, bool) or not (0 <= index < len(TIMEZONES)):
        return None
    return index


def valid_kind(kind: str) -> str | None:
    """None for anything but "expense"/"income" -- reject with Errors.BAD_SELECTION."""
    return kind if kind in KINDS else None


def valid_mode(mode: str) -> str | None:
    """None for anything but today/yesterday/date. A crafted mode used to fall through
    start_add's `match` silently, or reach amount_entered and pick a wrong date."""
    return mode if mode in ADD_MODES else None

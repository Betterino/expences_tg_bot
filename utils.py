import html
from calendar import monthrange
from datetime import date, datetime
from zoneinfo import ZoneInfo

from constants import PER_PAGE

ELLIPSIS = "…"


def visible(text: str) -> str:
    """The form the user actually sees -- what we measure and slice against.

    Category names and nicknames are html.escape()d at INPUT time
    (handlers/edit.py:146, handlers/settings.py:91) and stored escaped in SQLite, so
    "Кафе & бары" lives in the DB as "Кафе &amp; бары". Anything that measures or
    displays that string needs to unescape first, or "&" silently costs 5 columns
    instead of 1.
    """
    return html.unescape(str(text))


def fit(text: str, limit: int) -> str:
    """Truncate to `limit` visible columns and return HTML-safe output.

    Cutting happens before re-escaping, so an entity can never be split in half
    (truncating an already-escaped string can leave a dangling "&am").
    """
    raw = visible(text)
    if len(raw) <= limit:
        return html.escape(raw, quote=False)
    if limit <= 0:
        return ""
    return html.escape(raw[: limit - 1], quote=False) + ELLIPSIS


def clean_user_text(text: str | None, limit: int) -> str | None:
    """Strip, measure and HTML-escape free-text user input in one place (SEC-6).

    Category names and nicknames used to be html.escape()d at each call site
    separately -- one with quote=True (the html.escape default), fit() with
    quote=False, so a `"` ended up stored two different ways depending on which
    branch ran, which made the duplicate-name check miss. It also measured the
    escaped string's length against the limit, so "&&&&" (4 visible chars, 20
    escaped) got truncated as if it were 20 chars long (BUG-8). Routing every
    call through fit() fixes both: one escaping policy, length measured against
    what the user actually sees.

    Returns None for empty input so callers can branch on "nothing was typed"
    without re-checking falsiness of an escaped string.
    """
    raw = (text or "").strip()
    if not raw:
        return None
    return fit(raw, limit)


# 1 млрд ₽ in kopeks -- comfortably above any real expense, comfortably below
# SQLite's 64-bit INTEGER ceiling. A term above this used to parse fine (Python ints
# are unbounded) and only fail at bind time with an unhandled OverflowError (SEC-7).
MAX_TERM = 10**11


def _parse_term(text: str) -> int | None:
    try:
        text = text.replace(".",",")
        values = text.split(",")

        if len(values) > 2:
            return None
        else:
            if len(values) > 1:
                if len(values[1]) > 2:
                    return None
                else:
                    frac = values[1].ljust(2, "0")
                    result = int(values[0]) * 100 + int(frac)
            else:
                result = int(values[0]) * 100
    except(ValueError, AttributeError):
        return None
    return result if abs(result) < MAX_TERM else None


def parse_amount_terms(text: str) -> list[int] | None:
    """Split on '+' and parse each term, so "100+250+80" records one purchase split
    across receipts instead of making the user sum it on a calculator first.

    A leading unary '+' ("+100") still means "100", not "invalid" -- so an empty
    first term is dropped when there's more than one term. Any other empty term
    ("100+", "100++50") makes the whole input invalid.
    """
    try:
        parts = [p.strip() for p in text.split("+")]
    except AttributeError:
        return None
    if len(parts) > 1 and parts[0] == "":
        parts = parts[1:]
    if any(p == "" for p in parts):
        return None
    terms = [_parse_term(p) for p in parts]
    if any(t is None for t in terms):
        return None
    return terms


def parse_amount(text: str) -> int|None:
    terms = parse_amount_terms(text)
    return None if terms is None else sum(terms)

def format_tx_date(date_str: str) -> str:
    return date.fromisoformat(date_str).strftime("%d.%m.%Y")

def format_money(value: int, sep: str = "") -> str:
    """Format kopeks as rubles,kopeks. `sep` groups thousands (e.g. narrow nbsp).

    Sign is handled via abs() + a re-attached prefix rather than // and % directly:
    Python floors negative division, so -1205 // 100 == -13 and -1205 % 100 == 95,
    which used to render -1205 as "-13,95" instead of "-12,05".
    """
    sign = "-" if value < 0 else ""
    value = abs(value)
    rubles = value // 100
    kopeiki = value % 100
    rub_text = f"{rubles:,}".replace(",", sep) if sep else str(rubles)
    if kopeiki > 0:
        text = f"{rub_text},{kopeiki:02d}"
    else:
        text = rub_text
    return sign + text

def stats_bounds(start_year,start_month,end_year,end_month) ->tuple[str,str]:
    last_day = monthrange(end_year, end_month)[1]
    return f"{start_year}-{start_month:02d}-01", f"{end_year}-{end_month:02d}-{last_day:02d}"

def year_bounds(year) -> tuple[str,str]:
    return f"{year}-01-01",f"{year}-12-31"

def shift_month(year,month,delta) -> tuple[int,int]:
    new_month = (year * 12 + month + delta - 1) % 12 + 1
    new_year = ((year * 12 + month + delta) - new_month) // 12
    return new_year,new_month

def page_count(total: int) -> int:
    return total // PER_PAGE + (1 if total % PER_PAGE != 0 else 0)

def calc_page(categories,page):
    return categories[PER_PAGE * (page - 1) : PER_PAGE * page]

def today(tz_name: str):
    return datetime.now(ZoneInfo(tz_name)).date()

def parse_date(date_str:str,timezone):
    now = today(timezone)
    try:
        arr = date_str.strip().split(".")
        day = int(arr[0])
        month = int(arr[1])
    except (AttributeError, ValueError, IndexError):
        return None
    for year in (now.year, now.year - 1):
        try:
            guess = date(year, month, day)
        except ValueError:
            continue
        if guess <= now:
            return guess
    return None

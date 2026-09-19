from calendar import monthrange
from datetime import datetime, date
from zoneinfo import ZoneInfo
import html
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


def parse_amount(text: str) -> int|None:
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
                    return int(values[0]) *100 + int(frac)
            else:
                return int(values[0]) * 100
    except(ValueError, AttributeError):
        return None
    
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
    return f"{start_year}-{start_month:02d}-01", f"{end_year}-{end_month:02d}-{monthrange(end_year,end_month)[1]:02d}"

def year_bounds(year) -> tuple[str,str]:
    return f"{year}-01-01",f"{year}-12-31"

def shift_month(year,month,delta) -> tuple[int,int]:
    new_month = (year * 12 + month + delta - 1) % 12 + 1
    new_year = ((year * 12 + month + delta) - new_month) // 12
    return new_year,new_month

def calc_page(categories,page):
    size = len(categories)
    new_categories = []
    i = PER_PAGE*(page-1)
    while i < min(size,PER_PAGE*(page)):
        new_categories.append(categories[i])
        i += 1
    return new_categories

def today(tz_name: str):
    return datetime.now(ZoneInfo(tz_name)).date()

def parse_date(date_str:str,timezone):
    now = today(timezone)
    arr = date_str.strip().split(".")
    try:
        day = int(arr[0])
        month = int(arr[1])
    except ValueError:
        return None
    for year in (now.year, now.year - 1):
        try:
            guess = date(year, month, day)
        except ValueError:
            continue
        if guess <= now:
            return guess
    return None
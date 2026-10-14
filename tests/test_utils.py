import pathlib

from utils import clean_user_text, format_money, parse_amount, parse_amount_terms, parse_date


def test_utils() -> None:
    assert parse_amount("250") == 25000
    assert parse_amount("5,5") == 550
    assert parse_amount("5,50") == 550
    assert parse_amount("12,05") == 1205
    assert parse_amount("абв") is None
    assert parse_amount("") is None
    assert parse_amount("1.2.3") is None
    assert format_money(25000) == "250"
    assert format_money(-1205) == "-12,05"  # regression: floor division used to give "-13,95"
    assert format_money(1205) == "12,05"
    assert format_money(12340, sep=" ") == "123,40"  # sep groups thousands, not fraction digits
    assert format_money(1234000, sep=" ") == "12 340"


def test_parse_amount_plus() -> None:
    assert parse_amount("100+250+80") == 43000
    assert parse_amount("100 + 250") == 35000  # пробелы вокруг '+' допустимы
    assert parse_amount("5,5+5,5") == 1100     # дроби считаются по каждому слагаемому
    assert parse_amount("+100") == 10000       # ведущий унарный '+' -- не разделитель
    assert parse_amount("100+") is None
    assert parse_amount("100++50") is None
    assert parse_amount("") is None


def test_parse_amount_terms() -> None:
    assert parse_amount_terms("100+250") == [10000, 25000]
    assert parse_amount_terms("абв") is None


def test_parse_amount_rejects_huge_terms() -> None:
    """SEC-7: a term parses fine as a Python int no matter how many digits, but SQLite's
    INTEGER is 64-bit -- an unbounded term used to reach bind time and raise OverflowError."""
    assert parse_amount("9" * 4000) is None
    assert parse_amount("1" + "0" * 20) is None
    assert parse_amount("100+" + "9" * 4000) is None  # one huge term invalidates the whole sum
    assert parse_amount("100000000") is not None       # comfortably under the cap still works


def test_parse_date_rejects_non_text() -> None:
    """BUG-4: a sticker/photo at the date prompt gives message.text=None --
    parse_date used to call None.strip() and raise AttributeError."""
    assert parse_date(None, "UTC") is None
    assert parse_date("не дата", "UTC") is None
    assert parse_date("15", "UTC") is None  # no "." -- used to IndexError on arr[1]
    assert parse_date("15.03", "UTC") is not None


def test_clean_user_text() -> None:
    """SEC-6/BUG-8: one escaping policy, length measured against what the user
    actually sees (not the escaped string)."""
    assert clean_user_text(None, 15) is None
    assert clean_user_text("   ", 15) is None            # whitespace-only -> None
    assert clean_user_text("Кафе & бары", 15) == "Кафе &amp; бары"
    # "&&&&" is 4 visible chars -- must NOT be truncated at a 15-char limit just
    # because its escaped form ("&amp;" x4 = 20 chars) is longer than the limit.
    assert clean_user_text("&&&&", 15) == "&amp;&amp;&amp;&amp;"
    long = clean_user_text("а" * 30, 20)
    assert len(long) == 20
    assert long.endswith("…")


def test_no_handler_calls_html_escape_directly() -> None:
    """SEC-6: clean_user_text() is the one place free-text user input gets escaped --
    a call site reaching for html.escape() directly would bypass its length-measured-
    against-visible-text fix (BUG-8) and its single, consistent quote= policy."""
    handlers_dir = pathlib.Path(__file__).resolve().parent.parent / "handlers"
    for path in handlers_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "html.escape" not in text, path

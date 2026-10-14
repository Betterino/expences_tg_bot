"""Data -> rich blocks. Pure functions, no aiogram calls, no DB, no I/O.

handlers/screens.py is the only place that knows these blocks need to go inside an
InputRichMessage and get sent through Bot API -- everything here just builds the
tree, which is why it can be unit-tested without a bot or a database.
"""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import richtext
from texts import About, Categories, History, Screens, Stats
from utils import format_money, format_tx_date, visible

SEP = "\xa0"  # неразрывный пробел как разделитель разрядов: 12 340, а не 12340


@dataclass(frozen=True, slots=True)
class TableData:
    """Everything a stats renderer is allowed to see, in one frozen envelope.

    expense/income rows are index-by-name mappings. aiosqlite.Row and plain dict both
    satisfy that, which is why hardcoded fixtures (sandbox/fixtures.py) and real DB
    rows are interchangeable here without any adapter layer.
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


def _period(data: TableData) -> str:
    return f"{format_tx_date(data.start)} — {format_tx_date(data.end)}"


def _verdict(data: TableData) -> str:
    return Stats.SURPLUS if data.diff >= 0 else Stats.DEFICIT


def _money_table(rows: Sequence[Mapping], columns: list[str], total: int, has_max: bool) -> richtext.Block:
    body = []
    for r in rows:
        row = [visible(r["name"]), format_money(r["total"], sep=SEP)]
        if has_max:
            row.append(format_money(r["maximum"], sep=SEP) if r["maximum"] else "—")
        body.append(row)
    total_row = ["Всего", format_money(total, sep=SEP)]
    if has_max:
        total_row.append("")
    body.append(total_row)
    return richtext.table(columns, body)


def stats_view(data: TableData) -> list[richtext.Block]:
    expense_columns = [Categories.NAME_COLUMN, Stats.TOTAL_COLUMN, Categories.MAX_COLUMN]
    income_columns = [Categories.NAME_COLUMN, Stats.INCOME_COLUMN]
    return [
        richtext.para(f"Статистика · {_period(data)}"),
        _money_table(data.expense, expense_columns, data.total_e, has_max=True),
        richtext.divider(),
        _money_table(data.income, income_columns, data.total_i, has_max=False),
        richtext.footer(f"Итого: {format_money(data.diff, sep=SEP)} — у вас {_verdict(data)}"),
    ]


def history_view(
    rows: Sequence[Mapping],
    page: int,
    max_page: int,
    kind: str | None = None,
    who: str = "all",
    sort: str = "id",
) -> list[richtext.Block]:
    if not rows:
        return [richtext.para(History.EMPTY)]
    filters = " · ".join(
        (History.WHO_LABELS[who], History.KIND_LABELS[kind], History.SORT_LABELS[sort])
    )
    header = f"История · {filters} · {Screens.PAGE.format(page=page, max_page=max_page)}"
    has_who = who != "mine"  # свой фильтр "мои" -> колонка "Кто" избыточна
    columns = [History.DATE_COLUMN, History.AMOUNT_COLUMN, History.CATEGORY_COLUMN]
    aligns = ["left", "right", "left"]
    if has_who:
        columns.append(History.KTO_COLUMN)
        aligns.append("left")
    body = []
    for r in rows:
        amount = -r["amount"] if r["kind"] != "income" else r["amount"]
        row = [
            format_tx_date(r["date"]),
            format_money(amount, sep=SEP),
            visible(r["category_name"]) if r["category_name"] else History.NO_CATEGORY,
        ]
        if has_who:
            who_text = visible(r["nickname"]) if r["nickname"] else f"ID {r['added_by']}"
            row.append(who_text)
        body.append(row)
    return [
        richtext.para(header),
        richtext.table(columns, body, aligns=aligns),
    ]


def menu_view() -> list[richtext.Block]:
    """Menu title + a collapsed 'what does each button do' table.

    Collapsed by default (`is_open=False`) rather than an always-expanded block or a
    separate screen -- the user knows the buttons already after the first few uses,
    so the explanation should be one tap away, not always on screen.
    """
    rows = [[visible(label), visible(desc)] for label, desc in Screens.MENU_HELP]
    return [
        richtext.para(Screens.MENU_TITLE),
        richtext.details(
            Screens.MENU_HELP_SUMMARY,
            [richtext.table(Screens.MENU_HELP_COLUMNS, rows, aligns=["left", "left"])],
            is_open=False,
        ),
    ]


def about_view(version: str, summary: str, url: str) -> list[richtext.Block]:
    blocks: list[richtext.Block] = [
        richtext.heading(About.TITLE),
        richtext.para(About.VERSION_LINE.format(version=version)),
        richtext.para(visible(summary)),
    ]
    if url:
        blocks.append(richtext.footer(f"{About.CHANGELOG_LINK}: {url}"))
    return blocks


def categories_view(categories: Sequence[Mapping], kind: str, prefix: str = "") -> list[richtext.Block]:
    active = [r for r in categories if r["is_archived"] == 0]
    archived = [r for r in categories if r["is_archived"] != 0]
    has_max = kind == "expense"
    columns = [Categories.NAME_COLUMN, Categories.MAX_COLUMN] if has_max else [Categories.NAME_COLUMN]

    def rows_for(cats: Sequence[Mapping]) -> list[list[str]]:
        out = []
        for r in cats:
            name = visible(r["name"])
            out.append([name, format_money(r["maximum"], sep=SEP)] if has_max else [name])
        return out

    blocks: list[richtext.Block] = []
    if prefix:
        blocks.append(richtext.para(prefix))
    blocks.append(richtext.heading(Categories.ACTIVE_HEADER))
    blocks.append(richtext.table(columns, rows_for(active)))
    blocks.append(richtext.heading(Categories.ARCHIVED_HEADER))
    blocks.append(richtext.table(columns, rows_for(archived)))
    return blocks

"""Data -> rich blocks. Pure functions, no aiogram calls, no DB, no I/O.

handlers/screens.py is the only place that knows these blocks need to go inside an
InputRichMessage and get sent through Bot API -- everything here just builds the
tree, which is why it can be unit-tested without a bot or a database.
"""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import richtext
from texts import Categories, History, Screens, Stats
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


def history_view(rows: Sequence[Mapping], page: int, max_page: int) -> list[richtext.Block]:
    if not rows:
        return [richtext.para(History.EMPTY)]
    header = f"История · {Screens.PAGE.format(page=page, max_page=max_page)}"
    columns = ["Дата", "Сумма", "Категория", "Кто"]
    body = []
    for r in rows:
        amount = -r["amount"] if r["kind"] != "income" else r["amount"]
        who = visible(r["nickname"]) if r["nickname"] else f"ID {r['added_by']}"
        body.append(
            [
                format_tx_date(r["date"]),
                format_money(amount, sep=SEP),
                visible(r["category_name"]) if r["category_name"] else "Без категории",
                who,
            ]
        )
    return [
        richtext.para(header),
        richtext.table(columns, body, aligns=["left", "right", "left", "left"]),
    ]


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

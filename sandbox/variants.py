"""The variant registry and every candidate rendering style.

Adding a style is one decorator + one function. The keyboard and the dispatch both
derive from VARIANTS, so nothing else in the package is ever edited -- that is the
whole point of this sandbox, since we expect to iterate on styles many times.

Every render function is pure: TableData -> str. No aiogram, no DB, no I/O.
"""
from collections.abc import Callable
from dataclasses import dataclass

from aiogram.types import (
    InputRichBlockDetails,
    InputRichBlockDivider,
    InputRichBlockFooter,
    InputRichBlockList,
    InputRichBlockListItem,
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichMessage,
)

import richtext
from sandbox import TableData
from sandbox.helpers import bar, fit, lpad, money, percent, rpad, visible
from texts import Categories, Stats
from utils import format_tx_date
from views import stats_view

SEP = " "  # неразрывный пробел как разделитель разрядов: 12 340, а не 12340


Body = str | InputRichMessage


@dataclass(frozen=True, slots=True)
class Variant:
    key: str  # короткий ascii-ключ, уезжает в callback data
    label: str  # текст кнопки
    render: Callable[[TableData], Body]


VARIANTS: list[Variant] = []


def variant(key: str, label: str):
    """Register a renderer.

    The uniqueness assert fires at import time -- i.e. at bot start and at test
    collection -- so a copy-pasted key surfaces immediately instead of as a
    mysteriously dead button.
    """

    def decorator(fn: Callable[[TableData], Body]) -> Callable[[TableData], Body]:
        assert all(v.key != key for v in VARIANTS), f"дубль ключа варианта: {key}"
        VARIANTS.append(Variant(key=key, label=label, render=fn))
        return fn

    return decorator


def get(key: str) -> Variant:
    """Look up a variant, falling back to the first one instead of raising.

    Inline keyboards live in a Telegram chat forever, so a user will eventually tap a
    button for a variant that was deleted twenty minutes ago. A fallback beats a
    KeyError bubbling up to @dp.error().
    """
    return next((v for v in VARIANTS if v.key == key), VARIANTS[0])


def render(key: str, data: TableData) -> Body:
    return get(key).render(data)


def period(data: TableData) -> str:
    return f"{format_tx_date(data.start)} — {format_tx_date(data.end)}"


def verdict(data: TableData) -> str:
    return Stats.SURPLUS if data.diff >= 0 else Stats.DEFICIT


# --------------------------------------------------------------------------- 0 base


@variant("base", "0 Как было до rich")
def render_base(data: TableData) -> str:
    """Контрольный образец: то, чем был utils.create_stats_text до перехода на rich.

    Больше не используется в проде (см. views.py) -- живёт здесь как «до/после» для
    сравнения. Column drift на "Кафе &amp; бары" воспроизведён намеренно: это ровно
    та проблема, из-за которой считалась ширина по len() экранированной строки.
    """
    from utils import format_money as _format_money

    start, end, total_e, expense, income, total_i = (
        data.start,
        data.end,
        data.total_e,
        data.expense,
        data.income,
        data.total_i,
    )
    text = ""
    text += f"Статистика за период\n{start} - {end}\n<code>{Categories.NAME_COLUMN:<18}|{Stats.TOTAL_COLUMN:<12}|{Categories.MAX_COLUMN:<12}\n"
    for r in expense:
        if r["maximum"] != 0:
            text += f"{r['name']:<18}|{_format_money(r['total']):<12}|{_format_money(r['maximum']):<12}\n"
        else:
            text += f"{r['name']:<18}|{_format_money(r['total']):<12}\n"
    text += f"Всего: {_format_money(total_e):<12}"
    text += "</code>\n"
    text += f"\n<code>{Categories.NAME_COLUMN:<18}|{Stats.INCOME_COLUMN:<12}\n"
    for r in income:
        text += f"{r['name']:<18}|{_format_money(r['total']):<12}\n"
    text += f"Всего: {_format_money(total_i):<12}"
    diff = total_i - total_e
    text += f"\nИтого: {_format_money(diff):<12} У вас {Stats.SURPLUS if diff >= 0 else Stats.DEFICIT}"
    return text + "</code>"


# ---------------------------------------------------------------------------- 1 pre


@variant("pre", "1 pre-блок")
def render_pre(data: TableData) -> str:
    """Та же вёрстка, что сейчас, но <pre> вместо <code> и честные ширины.

    Tests: does <pre> look better than <code> for the exact same 44-column layout?
    <pre> is guaranteed block-level and gets a copy button on most clients; <code>
    flows inline. Tradeoff: extra vertical padding around the block.
    """
    out = [f"Статистика за период\n{period(data)}", "<pre>"]
    out.append(f"{rpad(Categories.NAME_COLUMN, 18)}|{rpad(Stats.TOTAL_COLUMN, 12)}|{Categories.MAX_COLUMN}")
    for r in data.expense:
        row = f"{rpad(r['name'], 18)}|{rpad(money(r['total'], SEP), 12)}"
        if r["maximum"]:
            row += f"|{money(r['maximum'], SEP)}"
        out.append(row)
    out.append(f"Всего: {money(data.total_e, SEP)}")
    out.append("</pre>")
    out.append("<pre>")
    out.append(f"{rpad(Categories.NAME_COLUMN, 18)}|{Stats.INCOME_COLUMN}")
    for r in data.income:
        out.append(f"{rpad(r['name'], 18)}|{money(r['total'], SEP)}")
    out.append(f"Всего: {money(data.total_i, SEP)}")
    out.append(f"Итого: {money(data.diff, SEP)} — у вас {verdict(data)}")
    out.append("</pre>")
    return "\n".join(out)


# --------------------------------------------------------------------------- 2 grid

_GRID = (14, 10, 9)  # 43 колонки вместе с рамкой


def _grid_line(left: str, mid: str, right: str, widths) -> str:
    return left + mid.join("─" * (w + 2) for w in widths) + right


def _grid_row(cells, widths) -> str:
    body = " │ ".join(
        rpad(c, w) if i == 0 else lpad(c, w) for i, (c, w) in enumerate(zip(cells, widths))
    )
    return f"│ {body} │"


@variant("grid", "2 Рамки")
def render_grid(data: TableData) -> str:
    """Настоящая таблица: рамки ┌─┬┐ и числа по правому краю.

    Tests: THE question -- does your phone scroll a wide code block horizontally, or
    wrap it? 39 columns is past the safe width, and one wrapped line shatters the
    whole grid. This is the variant to judge on a real device in portrait.
    """
    w3, w2 = _GRID, _GRID[:2]
    out = [f"<b>Статистика</b> {period(data)}", "<pre>"]
    out.append(_grid_line("┌", "┬", "┐", w3))
    out.append(_grid_row((Categories.NAME_COLUMN, Stats.TOTAL_COLUMN, Categories.MAX_COLUMN), w3))
    out.append(_grid_line("├", "┼", "┤", w3))
    for r in data.expense:
        maximum = money(r["maximum"], SEP) if r["maximum"] else "—"
        out.append(_grid_row((r["name"], money(r["total"], SEP), maximum), w3))
    out.append(_grid_line("├", "┼", "┤", w3))
    out.append(_grid_row(("Всего", money(data.total_e, SEP), ""), w3))
    out.append(_grid_line("└", "┴", "┘", w3))
    out.append(_grid_line("┌", "┬", "┐", w2))
    out.append(_grid_row((Categories.NAME_COLUMN, Stats.INCOME_COLUMN), w2))
    out.append(_grid_line("├", "┼", "┤", w2))
    for r in data.income:
        out.append(_grid_row((r["name"], money(r["total"], SEP)), w2))
    out.append(_grid_line("├", "┼", "┤", w2))
    out.append(_grid_row(("Всего", money(data.total_i, SEP)), w2))
    out.append(_grid_line("└", "┴", "┘", w2))
    out.append("</pre>")
    out.append(f"<b>Итого: {money(data.diff, SEP)}</b> — у вас {verdict(data)}")
    return "\n".join(out)


# ------------------------------------------------------------------------- 3 narrow

_NARROW = 30


def _leader(name: str, amount: str, total: int = _NARROW) -> str:
    return rpad(name, max(1, total - len(amount) - 1), filler=".") + " " + amount


@variant("narrow", "3 Узкий")
def render_narrow(data: TableData) -> str:
    """Бюджет 30 колонок: имя обрезается, пунктир ведёт к сумме.

    Tests: the opposite bet from "Рамки" -- guarantee it never wraps on any phone,
    and see whether that reads as tidy or as cramped. Tradeoff: the Максимум column
    does not fit at all, so budget overruns become invisible here.
    """
    out = [f"<b>{period(data)}</b>", "<code>"]
    out.append(Stats.TOTAL_COLUMN.upper())
    for r in data.expense:
        out.append(_leader(r["name"], money(r["total"], SEP)))
    out.append(_leader("ВСЕГО", money(data.total_e, SEP)))
    out.append("")
    out.append(Stats.INCOME_COLUMN.upper())
    for r in data.income:
        out.append(_leader(r["name"], money(r["total"], SEP)))
    out.append(_leader("ВСЕГО", money(data.total_i, SEP)))
    out.append("</code>")
    out.append(f"<b>Итого: {money(data.diff, SEP)}</b> — у вас {verdict(data)}")
    return "\n".join(out)


# --------------------------------------------------------------------------- 4 bars


@variant("bars", "4 Полоски")
def render_bars(data: TableData) -> str:
    """Полоса заполнения максимума: ███████░░░ 175%.

    Tests: whether "am I over budget" beats "what are the exact numbers" as the thing
    the stats screen should answer first. Tradeoff: costs a second line per category,
    and rows with maximum == 0 have no bar, so the block looks inhomogeneous.
    """
    out = [f"<b>{Stats.TOTAL_COLUMN}</b> · {period(data)}", "<code>"]
    for r in data.expense:
        out.append(f"{rpad(r['name'], 16)}{lpad(money(r['total'], SEP), 12)}")
        line = bar(r["total"], r["maximum"])
        if line:
            out.append(f"{line} {percent(r['total'], r['maximum'])} из {money(r['maximum'], SEP)}")
        else:
            out.append("░░░░░░░░░░ без максимума")
    out.append(f"{rpad('ВСЕГО', 16)}{lpad(money(data.total_e, SEP), 12)}")
    out.append("</code>")
    out.append(f"<b>{Stats.INCOME_COLUMN}</b>")
    out.append("<code>")
    for r in data.income:
        out.append(f"{rpad(r['name'], 16)}{lpad(money(r['total'], SEP), 12)}")
    out.append(f"{rpad('ВСЕГО', 16)}{lpad(money(data.total_i, SEP), 12)}")
    out.append("</code>")
    out.append(f"<b>Итого: {money(data.diff, SEP)}</b> — у вас {verdict(data)}")
    return "\n".join(out)


# --------------------------------------------------------------------------- 5 rich


@variant("rich", "5 Без моноширинного")
def render_rich(data: TableData) -> str:
    """Пропорциональный шрифт: только <b>, <i> и раскрывающаяся цитата.

    Tests: give up columns entirely and let Telegram lay the text out. Immune to
    wrapping at any screen width and the most "native chat" looking option.
    Tradeoff: you can no longer scan amounts vertically, and tag overhead eats the
    4096-character budget fastest of all variants.
    """
    out = [f"<b>Статистика</b> · <i>{period(data)}</i>", "", f"<b>{Stats.TOTAL_COLUMN}</b>"]
    out.append("<blockquote expandable>")
    for r in data.expense:
        tail = f" <i>из {money(r['maximum'], SEP)}</i>" if r["maximum"] else ""
        out.append(f"{fit(r['name'], 24)} — <b>{money(r['total'], SEP)}</b>{tail}")
    out.append("</blockquote>")
    out.append(f"Всего: <b>{money(data.total_e, SEP)}</b>")
    out.append("")
    out.append(f"<b>{Stats.INCOME_COLUMN}</b>")
    out.append("<blockquote expandable>")
    for r in data.income:
        out.append(f"{fit(r['name'], 24)} — <b>{money(r['total'], SEP)}</b>")
    out.append("</blockquote>")
    out.append(f"Всего: <b>{money(data.total_i, SEP)}</b>")
    out.append("")
    out.append(f"Итого: <b>{money(data.diff, SEP)}</b> — у вас <i>{verdict(data)}</i>")
    return "\n".join(out)


# -------------------------------------------------------------------------- 6 quote


@variant("quote", "6 Цитата")
def render_quote(data: TableData) -> str:
    """Моноширинная таблица внутри раскрывающейся цитаты.

    Tests: the cheapest fix for a 40-category month -- the table collapses to a few
    lines with a "развернуть" control instead of flooding the chat. Uses <code>, not
    <pre>: Telegram restricts what may nest inside a blockquote. Tradeoff: on older
    clients "expandable" degrades to an ordinary quote and nothing is saved.
    """
    out = [f"<b>Статистика</b> {period(data)}", "<blockquote expandable><code>"]
    out.append(f"{rpad(Categories.NAME_COLUMN, 16)}{lpad(Stats.TOTAL_COLUMN, 12)}")
    for r in data.expense:
        out.append(f"{rpad(r['name'], 16)}{lpad(money(r['total'], SEP), 12)}")
    out.append(f"{rpad('ВСЕГО', 16)}{lpad(money(data.total_e, SEP), 12)}")
    out.append("</code></blockquote>")
    out.append("<blockquote expandable><code>")
    out.append(f"{rpad(Categories.NAME_COLUMN, 16)}{lpad(Stats.INCOME_COLUMN, 12)}")
    for r in data.income:
        out.append(f"{rpad(r['name'], 16)}{lpad(money(r['total'], SEP), 12)}")
    out.append(f"{rpad('ВСЕГО', 16)}{lpad(money(data.total_i, SEP), 12)}")
    out.append("</code></blockquote>")
    out.append(f"<b>Итого: {money(data.diff, SEP)}</b> — у вас {verdict(data)}")
    return "\n".join(out)


# ------------------------------------------------------------------ 7 rich table


@variant("rtable", "7 Rich-таблица")
def render_rtable(data: TableData) -> InputRichMessage:
    """Тонкая обёртка над views.stats_view -- то, что реально уходит в прод.

    Не дублирует построение таблицы: если прод меняется, «вариант 7» меняется вместе
    с ним, а не расходится с реальным экраном статистики, как это было бы с
    отдельной копией _table_block. Requires Bot API 10.1+ (InputRichBlockTable).
    """
    return richtext.message(stats_view(data))


# --------------------------------------------------------------- 8 rich document


def _category_list(rows: list[dict]) -> InputRichBlockList:
    items = []
    for r in rows:
        tail = f" из {money(r['maximum'])}" if r["maximum"] else ""
        text = f"{visible(r['name'])} — {money(r['total'])}{tail}"
        items.append(InputRichBlockListItem(blocks=[InputRichBlockParagraph(text=text)]))
    return InputRichBlockList(items=items)


@variant("rdoc", "8 Rich-документ")
def render_rdoc(data: TableData) -> InputRichMessage:
    """Document-shaped alternative: headings, a divider, per-category lists, and the
    whole breakdown collapsible in a <details> block -- tests whether a long category
    list reads better collapsed than truncated (cf. sandbox's "6 Цитата" for the
    <pre>-inside-<blockquote> equivalent)."""
    breakdown = [
        InputRichBlockSectionHeading(text=Stats.TOTAL_COLUMN, size=4),
        _category_list(data.expense),
        InputRichBlockParagraph(text=f"Всего: {money(data.total_e)}"),
        InputRichBlockSectionHeading(text=Stats.INCOME_COLUMN, size=4),
        _category_list(data.income),
        InputRichBlockParagraph(text=f"Всего: {money(data.total_i)}"),
    ]
    blocks: list = [
        InputRichBlockSectionHeading(text="Статистика", size=2),
        InputRichBlockParagraph(text=period(data)),
        InputRichBlockDivider(),
        InputRichBlockDetails(summary="Разбивка по категориям", blocks=breakdown, is_open=True),
        InputRichBlockFooter(text=f"Итого: {money(data.diff)} — у вас {verdict(data)}"),
    ]
    return InputRichMessage(blocks=blocks)

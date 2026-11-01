"""Pure primitives for building rich Bot API messages (InputRichMessage blocks).

No aiogram-side effects, no DB, no I/O -- just aiogram.types constructors plus the
few invariants Telegram enforces and will not tell you about until the sendRichMessage
call fails: every row of a table must have the same width, and the message has a
combined text budget across every block. This is the tool: any future table
prototypes in sandbox/variants.py against these same functions before it graduates
to views.py, so the sandbox and production never draw from two different builders.
"""
from collections.abc import Iterable, Iterator

from aiogram.types import (
    InputRichBlockDetails,
    InputRichBlockDivider,
    InputRichBlockFooter,
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichBlockTable,
    InputRichMessage,
    RichBlockTableCell,
)

RICH_LIMIT = 32768  # суммарная длина текста во всех блоках сообщения
MAX_BLOCKS = 500
MAX_COLUMNS = 20

Block = (
    InputRichBlockParagraph
    | InputRichBlockDivider
    | InputRichBlockFooter
    | InputRichBlockSectionHeading
    | InputRichBlockTable
    | InputRichBlockDetails
)


def para(text: str) -> InputRichBlockParagraph:
    return InputRichBlockParagraph(text=text)


def heading(text: str, size: int = 3) -> InputRichBlockSectionHeading:
    return InputRichBlockSectionHeading(text=text, size=size)


def divider() -> InputRichBlockDivider:
    return InputRichBlockDivider()


def footer(text: str) -> InputRichBlockFooter:
    return InputRichBlockFooter(text=text)


def details(summary: str, blocks: list[Block], is_open: bool = False) -> InputRichBlockDetails:
    return InputRichBlockDetails(summary=summary, blocks=blocks, is_open=is_open)


def table(
    columns: list[str],
    rows: list[list[str]],
    aligns: list[str] | None = None,
    bordered: bool = True,
    striped: bool = True,
) -> InputRichBlockTable:
    """Build a table block. `columns` is the header row; `rows` are data rows (all
    plain strings -- format money/dates/etc. before calling this).

    `aligns` defaults to left for column 0 and right for the rest (name column,
    then numbers) since every current caller shapes data that way. Pass it
    explicitly to override.

    Asserts every row is the same width as the header: Telegram silently rejects a
    ragged table, and that is the one thing about this API worth failing loudly on
    at build time instead of at the sendRichMessage call.
    """
    width = len(columns)
    assert width <= MAX_COLUMNS, f"слишком много колонок: {width} > {MAX_COLUMNS}"
    if aligns is None:
        aligns = ["left"] + ["right"] * (width - 1)
    assert len(aligns) == width, "aligns должен быть той же длины, что columns"

    def make_row(values: list[str], is_header: bool) -> list[RichBlockTableCell]:
        assert len(values) == width, f"строка таблицы шириной {len(values)}, а не {width}"
        return [
            RichBlockTableCell(align=align, valign="middle", text=text, is_header=is_header)
            for text, align in zip(values, aligns)
        ]

    cells = [make_row(columns, is_header=True)]
    cells.extend(make_row(row, is_header=False) for row in rows)
    return InputRichBlockTable(cells=cells, is_bordered=bordered, is_striped=striped)


def message(blocks: list[Block]) -> InputRichMessage:
    return InputRichMessage(blocks=blocks)


def walk_text(blocks: Iterable) -> Iterator[str]:
    """Yield every literal text string found in a rich block tree.

    Walks the handful of fields that can carry text or nested blocks (table cells
    are a list of lists, details wraps further blocks) instead of assuming a fixed
    shape, since the tree differs per block type.
    """
    for obj in blocks if isinstance(blocks, (list, tuple)) else [blocks]:
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, list):
            yield from walk_text(obj)
        elif hasattr(obj, "model_dump"):
            for attr in ("text", "blocks", "cells", "items", "caption", "summary"):
                value = getattr(obj, attr, None)
                if value is not None:
                    yield from walk_text(value)


def count_blocks(blocks: list[Block]) -> int:
    return len(blocks)


def text_len(blocks: list[Block]) -> int:
    return sum(len(t) for t in walk_text(blocks))

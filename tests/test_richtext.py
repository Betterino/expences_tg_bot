"""Property tests for views.py x hostile fixtures.

Mirrors tests/test_sandbox.py's invariants (block/column/text limits, exactly one
InputRichMessage content field) but targets the production views instead of the
sandbox's style gallery -- these are the three screens that actually ship.
"""
import richtext
from sandbox.fixtures import CATEGORY_ROWS, FIXTURES, HISTORY_ROWS
from views import categories_view, history_view, stats_view


def _all_screens():
    for name, data in FIXTURES.items():
        yield f"stats/{name}", stats_view(data)
    yield "history/rows", history_view(HISTORY_ROWS, page=1, max_page=1)
    yield "history/empty", history_view([], page=1, max_page=1)
    yield "categories/expense", categories_view(CATEGORY_ROWS, "expense")
    yield "categories/income", categories_view(CATEGORY_ROWS, "income")
    yield "categories/prefix", categories_view(CATEGORY_ROWS, "expense", prefix="Добавил Кафе")


def test_every_screen_uses_exactly_one_content_field() -> None:
    for label, blocks in _all_screens():
        body = richtext.message(blocks)
        used = [f for f in (body.html, body.markdown, body.blocks) if f is not None]
        assert len(used) == 1, f"{label}: {len(used)} полей вместо одного"


def test_every_screen_respects_block_and_column_limits() -> None:
    for label, blocks in _all_screens():
        count, limit = richtext.count_blocks(blocks), richtext.MAX_BLOCKS
        assert count <= limit, f"{label}: {count} блоков > {limit}"
        for block in blocks:
            cells = getattr(block, "cells", None)
            if cells is not None:
                for row in cells:
                    width, max_width = len(row), richtext.MAX_COLUMNS
                    assert width <= max_width, f"{label}: строка шириной {width} > {max_width}"


def test_every_table_has_uniform_row_width() -> None:
    for label, blocks in _all_screens():
        for block in blocks:
            cells = getattr(block, "cells", None)
            if cells is not None:
                widths = {len(row) for row in cells}
                assert len(widths) == 1, f"{label}: неровные строки таблицы {widths}"


def test_every_screen_fits_rich_limit() -> None:
    for label, blocks in _all_screens():
        assert richtext.text_len(blocks) <= richtext.RICH_LIMIT, f"{label}: превышен лимит текста"


def test_every_screen_unescapes_its_text() -> None:
    """Regression guard for the accepted escape-at-input decision: rich block text is
    literal RichText, not markup, so a category name stored HTML-escaped must come
    back through utils.visible() before landing in a block -- otherwise "Кафе &amp;
    бары" renders literally instead of "Кафе & бары"."""
    for label, blocks in _all_screens():
        for text in richtext.walk_text(blocks):
            assert "&amp;" not in text, f"{label}: неснятый &amp;"
            assert "&lt;" not in text, f"{label}: неснятый &lt;"


def test_history_view_falls_back_for_missing_nickname_and_category() -> None:
    blocks = history_view(HISTORY_ROWS, page=1, max_page=1)
    text = "".join(richtext.walk_text(blocks))
    assert "ID 42" in text  # запись без никнейма
    assert "Без категории" in text  # запись с удалённой категорией


def test_history_view_empty_shows_placeholder() -> None:
    from texts import History

    blocks = history_view([], page=1, max_page=1)
    text = "".join(richtext.walk_text(blocks))
    assert History.EMPTY in text


def test_stats_view_deficit_month_keeps_correct_sign() -> None:
    blocks = stats_view(FIXTURES["deficit"])
    text = "".join(richtext.walk_text(blocks)).replace("\xa0", " ")
    assert "-20 000,05" in text  # -2000005 копеек -> "-20000,05", не "-19999,95"

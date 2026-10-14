"""History filters (kind/added_by) and sort (id/date), added as a screen-state cycle
carried entirely in HistoryPageCB -- no FSM, same pattern as the sandbox screen.

The discriminating fixture: insert a back-dated row LAST, so id order and date order
disagree. Without that, sort tests would pass vacuously.
"""

import richtext
from callback import HistoryPageCB
from constants import HISTORY_CYCLES
from db import Database
from handlers.history import history_page, open_history, render_history_screen
from keyboards import history_kb
from tests.fakes import FakeCallbackQuery, rich_blocks, unpack_callback_data
from views import history_view


async def _seed(db: Database):
    await db.ensure_user(111)
    await db.ensure_user(222)
    await db.set_nickname(111, "Вася")
    budget_id = await db.create_budget(111)
    await db.add_to_budget(222, budget_id)
    cat_id = (await db.list_active_categories(budget_id, "expense"))[0]["category_id"]
    income_cat_id = (await db.list_active_categories(budget_id, "income"))[0]["category_id"]

    id1 = await db.add_expense(budget_id, 111, cat_id, 10000, "2026-03-10", "expense")
    id2 = await db.add_expense(budget_id, 222, income_cat_id, 20000, "2026-03-11", "income")
    # back-dated, added last
    id3 = await db.add_expense(budget_id, 111, cat_id, 5000, "2026-03-01", "expense")
    return budget_id, (id1, id2, id3)


async def test_sort_id_vs_date_disagree(db: Database) -> None:
    budget_id, (id1, id2, id3) = await _seed(db)

    by_id = await db.list_recent_transactions(budget_id, 10, 0, sort="id")
    assert [r["expense_id"] for r in by_id] == [id3, id2, id1]

    by_date = await db.list_recent_transactions(budget_id, 10, 0, sort="date")
    assert [r["expense_id"] for r in by_date] == [id2, id1, id3]


async def test_added_by_filters_list_and_count(db: Database) -> None:
    budget_id, _ = await _seed(db)

    mine = await db.list_recent_transactions(budget_id, 10, 0, added_by=111)
    assert all(r["added_by"] == 111 for r in mine)
    assert len(mine) == 2

    assert await db.count_transactions(budget_id, added_by=111) == 2
    assert await db.count_transactions(budget_id, added_by=None) == 3


async def test_kind_and_added_by_and_sort_combine_with_pagination(db: Database) -> None:
    budget_id, (id1, _, id3) = await _seed(db)

    rows = await db.list_recent_transactions(
        budget_id, limit=1, offset=0, kind="expense", added_by=111, sort="date"
    )
    assert len(rows) == 1 and rows[0]["expense_id"] == id1  # newest date first page (DESC)

    rows_p2 = await db.list_recent_transactions(
        budget_id, limit=1, offset=1, kind="expense", added_by=111, sort="date"
    )
    assert len(rows_p2) == 1 and rows_p2[0]["expense_id"] == id3

    assert await db.count_transactions(budget_id, kind="expense", added_by=111) == 2


async def test_count_transactions_is_int_and_does_not_raise(db: Database) -> None:
    """Regression guard for the invalid 'SORT BY' that once broke every COUNT(*) call."""
    budget_id, _ = await _seed(db)
    total = await db.count_transactions(budget_id)
    assert isinstance(total, int)


async def test_unknown_sort_falls_back_to_id(db: Database) -> None:
    budget_id, (id1, id2, id3) = await _seed(db)
    rows = await db.list_recent_transactions(budget_id, 10, 0, sort="'; DROP TABLE expenses; --")
    assert [r["expense_id"] for r in rows] == [id3, id2, id1]  # falls back to sort="id"


async def test_render_history_screen_with_each_filter(db: Database) -> None:
    budget_id, _ = await _seed(db)

    callback = FakeCallbackQuery(user_id=111)
    await render_history_screen(
        callback, db, budget_id, page=1, kind="expense", who="mine", sort="date"
    )

    blocks = rich_blocks(callback.message.edit_text)
    text = "".join(richtext.walk_text(blocks))
    assert "Мои" in text and "Траты" in text and "По дате" in text


async def test_who_mine_drops_kto_column() -> None:
    rows = [
        {
            "date": "2026-03-01", "amount": -100, "kind": "expense",
            "category_name": "Продукты", "nickname": "Аня", "added_by": 1,
        },
    ]
    blocks_all = history_view(rows, page=1, max_page=1, who="all")
    blocks_mine = history_view(rows, page=1, max_page=1, who="mine")

    table_all = next(b for b in blocks_all if getattr(b, "cells", None) is not None)
    table_mine = next(b for b in blocks_mine if getattr(b, "cells", None) is not None)
    assert len(table_all.cells[0]) == 4
    assert len(table_mine.cells[0]) == 3


def test_history_kb_toggle_round_trips_next_value_and_resets_page() -> None:
    markup = history_kb(page=3, max_page=5, kind=None, who="all", sort="id")
    who_cb = unpack_callback_data(markup, 0, 0, HistoryPageCB)
    kind_cb = unpack_callback_data(markup, 0, 1, HistoryPageCB)
    sort_cb = unpack_callback_data(markup, 0, 2, HistoryPageCB)
    for cb in (who_cb, kind_cb, sort_cb):
        assert cb.page == 1
    assert who_cb.who == "mine"
    assert kind_cb.kind == "expense"
    assert sort_cb.sort == "date"


def test_history_cycles_are_closed() -> None:
    for axis, cycle in HISTORY_CYCLES.items():
        for start in cycle:
            value = start
            for _ in range(len(cycle)):
                value, _label = cycle[value]
            assert value == start, f"{axis} cycle does not return to {start!r}"


async def test_open_history_and_history_page_render(db: Database) -> None:
    # Answering the callback query is CallbackAnswerMiddleware's job now (bot.py),
    # not the handler's -- see tests/test_callbacks.py for that guarantee.
    budget_id, _ = await _seed(db)

    callback = FakeCallbackQuery(user_id=111)
    await open_history(callback, db, budget_id)
    callback.message.edit_text.assert_awaited()

    callback2 = FakeCallbackQuery(user_id=111)
    await history_page(callback2, HistoryPageCB(page=1), db, budget_id)
    callback2.message.edit_text.assert_awaited()

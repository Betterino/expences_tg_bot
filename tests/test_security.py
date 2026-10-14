"""SEC-1/SEC-2/SEC-3: CallbackData factories are fully attacker-controlled -- Telegram
never verifies that the bytes in a callback_query came from a button we actually
rendered. These tests craft cross-budget ids and out-of-domain enum values the way an
attacker would (by hand, not by tapping a real button) and assert the boundary holds.
"""

from callback import CategoryCB, HistoryPageCB, MonthCB, StatsCB, TzCB
from db import Database
from handlers.edit import (
    CategoryMax,
    CategoryName,
    archive_category,
    edit_categories_delete,
    edit_categories_rename,
    input_category_max,
    input_category_name,
)
from handlers.expenses import amount_entered
from handlers.history import history_page
from handlers.settings import tz_chosen
from handlers.stats import StatsRange, display_page_stats, input_month, input_year
from tests.fakes import FakeCallbackQuery, FakeMessage, make_callback_answer, make_state
from texts import Errors


async def _two_budgets(db: Database):
    """Budget A owns one category; budget B belongs to a different, unrelated user."""
    await db.ensure_user(111)
    await db.ensure_user(222)
    budget_a = await db.create_budget(111)
    budget_b = await db.create_budget(222)
    cats_a = await db.list_active_categories(budget_a, "expense")
    category_id = cats_a[0]["category_id"]
    return budget_a, budget_b, category_id


async def test_db_mutations_are_scoped_to_budget(db: Database) -> None:
    budget_a, budget_b, category_id = await _two_budgets(db)

    # attacker (budget_b) invokes every mutation against budget_a's category id
    assert await db.archive_category(budget_b, category_id) == 0
    assert await db.dearchive_category(budget_b, category_id) == 0
    assert await db.rename_category(budget_b, category_id, "Захвачено") == 0
    assert await db.change_maximum(budget_b, category_id, 999) == 0
    assert await db.delete_category(budget_b, category_id) == 0

    cats_a = await db.list_active_categories(budget_a, "expense")
    assert category_id in [c["category_id"] for c in cats_a]  # still there, untouched
    assert cats_a[0]["name"] != "Захвачено"
    all_a = await db.all_categories(budget_a, "expense")
    assert all_a[0]["maximum"] != 999

    # the real owner's mutations still work -- scoping isn't over-restrictive
    assert await db.archive_category(budget_a, category_id) == 1


async def test_archive_handler_rejects_foreign_category(db: Database) -> None:
    budget_a, budget_b, category_id = await _two_budgets(db)

    callback = FakeCallbackQuery()
    state = make_state()
    callback_answer = make_callback_answer()
    callback_data = CategoryCB(id=category_id, purpose="archive", kind="expense")

    # attacker's own budget_id, but a crafted id from budget_a
    await archive_category(callback, db, state, callback_data, budget_b, callback_answer)

    assert callback_answer.text == Errors.NOT_FOUND
    cats_a = await db.list_active_categories(budget_a, "expense")
    assert category_id in [c["category_id"] for c in cats_a]  # not archived


async def test_rename_confirm_rejects_foreign_category(db: Database) -> None:
    budget_a, budget_b, category_id = await _two_budgets(db)

    callback = FakeCallbackQuery()
    state = make_state()
    await state.update_data(category_name="Захвачено")
    callback_answer = make_callback_answer()
    # crafted by hand: a "Да" button budget B was never shown, carrying A's id
    callback_data = CategoryCB(id=category_id, purpose="rename_confirm", kind="expense")

    await edit_categories_rename(callback, state, callback_data, db, budget_b, callback_answer)

    assert callback_answer.text == Errors.NOT_FOUND
    cats_a = await db.list_active_categories(budget_a, "expense")
    assert all(c["name"] != "Захвачено" for c in cats_a)


async def test_confirm_delete_rejects_foreign_category(db: Database) -> None:
    budget_a, budget_b, category_id = await _two_budgets(db)

    callback = FakeCallbackQuery()
    state = make_state()
    callback_answer = make_callback_answer()
    callback_data = CategoryCB(id=category_id, purpose="confirm_delete", kind="expense")

    await edit_categories_delete(callback, state, callback_data, db, budget_b, callback_answer)

    assert callback_answer.text == Errors.NOT_FOUND
    cats_a = await db.list_active_categories(budget_a, "expense")
    assert category_id in [c["category_id"] for c in cats_a]  # not deleted


async def test_input_category_max_rejects_foreign_category(db: Database) -> None:
    budget_a, budget_b, category_id = await _two_budgets(db)

    message = FakeMessage(text="999")
    state = make_state()
    await state.set_state(CategoryMax.waiting_max)
    await state.update_data(mode="", category_id=category_id, kind="expense")

    await input_category_max(message, state, db, budget_b)

    message.answer.assert_awaited_with(Errors.NOT_FOUND)
    all_a = await db.all_categories(budget_a, "expense")
    assert all_a[0]["maximum"] != 999


async def test_input_category_name_rename_rejects_foreign_category(db: Database) -> None:
    budget_a, budget_b, category_id = await _two_budgets(db)

    message = FakeMessage(text="Захвачено")
    state = make_state()
    await state.set_state(CategoryName.waiting_name)
    await state.update_data(mode="rename", category_id=category_id, kind="expense")

    await input_category_name(message, state, db, budget_b)

    message.answer.assert_awaited_with(Errors.NOT_FOUND)
    cats_a = await db.list_active_categories(budget_a, "expense")
    assert all(c["name"] != "Захвачено" for c in cats_a)


async def test_amount_entered_refuses_foreign_category(db: Database) -> None:
    """SEC-2: a foreign category_id smuggled into FSM data must not create an
    expense row in the attacker's own budget under someone else's category."""
    budget_a, budget_b, category_id = await _two_budgets(db)

    message = FakeMessage(text="100", user_id=222)
    state = make_state(user_id=222)
    await state.update_data(category_id=category_id, kind="expense", mode="today")

    await amount_entered(message, state, db, budget_b, "UTC")

    message.answer.assert_any_await(Errors.NOT_FOUND)
    assert await db.count_transactions(budget_b) == 0


async def test_history_page_normalizes_crafted_filters(db: Database) -> None:
    """SEC-3: HistoryPageCB(who="x"/kind="x"/sort="x") would otherwise KeyError in
    keyboards.history_kb / views.history_view, which only know the buttons' own values."""
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)

    callback = FakeCallbackQuery()
    callback_data = HistoryPageCB(page=1, kind="x", who="x", sort="x")

    await history_page(callback, callback_data, db, budget_id)  # must not raise

    callback.message.edit_text.assert_awaited_once()


async def test_tz_chosen_rejects_out_of_range_index(db: Database) -> None:
    """SEC-3: TzCB(index=-1) would otherwise wrap around (Python negative indexing)
    and silently apply the *last* timezone; TzCB(index=999) would IndexError."""
    user = await db.ensure_user(111)

    for bad_index in (-1, 999):
        callback = FakeCallbackQuery()
        callback_answer = make_callback_answer()
        callback_data = TzCB(index=bad_index)

        await tz_chosen(callback, callback_data, db, user, callback_answer)

        assert callback_answer.text == Errors.BAD_SELECTION
        callback.message.edit_text.assert_not_awaited()

    user_after = await db.ensure_user(111)
    assert user_after["timezone"] == user["timezone"]  # untouched


async def test_display_page_stats_rejects_crafted_bounds(db: Database) -> None:
    """SEC-3/SEC-7: StatsCB(year=10**9, month=13) would otherwise reach
    calendar.monthrange and raise ValueError."""
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)

    callback = FakeCallbackQuery()
    callback_answer = make_callback_answer()
    callback_data = StatsCB(year=10**9, month=13)

    await display_page_stats(callback, callback_data, db, budget_id, callback_answer)

    assert callback_answer.text == Errors.BAD_SELECTION
    callback.message.edit_text.assert_not_awaited()


async def test_input_month_rejects_crafted_index(db: Database) -> None:
    """SEC-3: MonthCB(month=99) would otherwise index MONTHS[99] and IndexError."""
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)

    callback = FakeCallbackQuery()
    state = make_state()
    callback_answer = make_callback_answer()
    callback_data = MonthCB(month=99, purpose="from")

    await input_month(callback, callback_data, state, db, budget_id, "UTC", callback_answer)

    assert callback_answer.text == Errors.BAD_SELECTION
    callback.message.edit_text.assert_not_awaited()


async def test_input_year_rejects_out_of_bounds_year(db: Database) -> None:
    """SEC-7: a year far outside any real calendar reaches calendar.monthrange via
    stats_bounds and raises ValueError/OverflowError if not clamped first."""
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)

    message = FakeMessage(text=str(10**9))
    state = make_state()
    await state.set_state(StatsRange.waiting_year)

    await input_year(message, state, db, budget_id)

    message.answer.assert_awaited_with(Errors.BAD_YEAR)
    message.answer_rich.assert_not_awaited()

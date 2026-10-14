
import richtext
from callback import MonthCB
from db import Database
from handlers.stats import input_month, input_year
from tests.fakes import FakeCallbackQuery, FakeMessage, make_callback_answer, make_state, rich_blocks


async def test_input_year_includes_both_totals(db: Database) -> None:
    """Regression test for the stats screen being built from only 4 of 6 required args."""
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)

    expense_cats = await db.list_active_categories(budget_id, "expense")
    income_cats = await db.list_active_categories(budget_id, "income")
    await db.add_expense(budget_id, 111, expense_cats[0]["category_id"], 25000, "2026-03-05", "expense")
    await db.add_expense(budget_id, 111, income_cats[0]["category_id"], 500000, "2026-03-01", "income")

    state = make_state()
    message = FakeMessage(text="2026")

    await input_year(message, state, db, budget_id)  # would raise TypeError before the fix

    message.answer_rich.assert_awaited_once()
    text = "".join(richtext.walk_text(rich_blocks(message.answer_rich))).replace("\xa0", "")
    assert "250" in text     # трата
    assert "5000" in text    # доход
    assert await state.get_data() == {}


async def test_input_month_to_without_from_reprompts(db: Database) -> None:
    """BUG-3: "from_month" lives in FSM *data*, not FSM *state* -- a state.clear()
    on any menu nav between the "from" and "to" taps used to make this KeyError."""
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)

    callback = FakeCallbackQuery()
    state = make_state()  # no update_data(from_month=...) -- simulates the wipe
    callback_answer = make_callback_answer()
    callback_data = MonthCB(month=5, purpose="to")

    await input_month(callback, callback_data, state, db, budget_id, "UTC", callback_answer)

    callback.message.edit_text.assert_awaited_once()  # re-prompt, not a crash

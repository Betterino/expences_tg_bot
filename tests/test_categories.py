
from callback import NavCB
from db import Database
from handlers.edit import choose_edit_categories, input_category_name
from handlers.screens import render_categories_screen
from tests.fakes import FakeCallbackQuery, FakeMessage, make_state
from texts import Categories, Errors


async def test_dearchive_respects_kind(db: Database) -> None:
    """Regression: dearchive branch always defaulted to kind='expense', hiding archived income categories."""
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)

    expense_cats = await db.list_active_categories(budget_id, "expense")
    income_cats = await db.list_active_categories(budget_id, "income")
    await db.archive_category(budget_id, expense_cats[0]["category_id"])   # Продукты
    await db.archive_category(budget_id, income_cats[0]["category_id"])    # Зарплата

    callback = FakeCallbackQuery()
    await render_categories_screen(callback, db, budget_id, "dearchive", 1, "income")

    markup = callback.message.edit_text.await_args.kwargs["reply_markup"]
    names = {btn.text for row in markup.inline_keyboard for btn in row}
    assert "Зарплата" in names
    assert "Продукты" not in names


async def test_edit_categories_refuses_without_budget(db: Database) -> None:
    """BUG-6: entering the edit flow with budget_id=None used to fall through to
    add_category(name, None, ...), inserting an orphan row with budget_id=NULL."""
    await db.ensure_user(111)  # no create_budget -- current_budget stays None

    callback = FakeCallbackQuery()
    state = make_state()
    callback_data = NavCB(to="edit", kind="expense")

    await choose_edit_categories(callback, state, callback_data, db, None)

    callback.message.answer.assert_awaited_once_with(Errors.NO_BUDGET)
    callback.message.edit_text.assert_not_awaited()


async def test_duplicate_name_check_is_kind_scoped(db: Database) -> None:
    """BUG-1: check_category_name/_archived were called without `kind`, defaulting to
    "expense" -- so an income category named like an existing expense one falsely
    warned "уже есть", while a genuine duplicate income name went undetected."""
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)
    assert await db.check_category_name(budget_id, "Продукты", "expense") is not None

    # "Продукты" already exists as an EXPENSE category -- creating an INCOME
    # category with the same name must not be flagged as a duplicate.
    state = make_state()
    await state.update_data(mode="create", kind="income")
    message = FakeMessage(text="Продукты")

    await input_category_name(message, state, db, budget_id)

    message.answer.assert_not_awaited()  # no "уже есть" warning
    message.answer_rich.assert_awaited_once()  # straight through to creation

    # a genuine duplicate WITHIN income must still be caught.
    state2 = make_state()
    await state2.update_data(mode="create", kind="income")
    message2 = FakeMessage(text="Зарплата")

    await input_category_name(message2, state2, db, budget_id)

    assert message2.answer.await_args.args[0] == Categories.NAME_EXISTS


async def test_new_income_category_sort_order_is_income_scoped(db: Database) -> None:
    """Regression: new category sort_order was computed from expense max even for income categories."""
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)

    # разводим максимумы по kind как можно дальше друг от друга
    await db.add_category("Огромная трата", budget_id, 0, 1000, "expense")
    income_max_before = await db.get_maximum_sort_order(budget_id, "income")

    state = make_state()
    await state.update_data(mode="create", kind="income")
    message = FakeMessage(text="Такси")

    await input_category_name(message, state, db, budget_id)

    assert await db.check_category_name(budget_id, "Такси", "income") is not None
    assert await db.get_maximum_sort_order(budget_id, "income") == income_max_before + 10

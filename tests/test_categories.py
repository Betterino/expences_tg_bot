import tempfile
from pathlib import Path

from db import Database
from handlers.edit import input_category_name
from handlers.screens import render_categories_screen
from tests.fakes import FakeCallbackQuery, FakeMessage, make_state


async def test_dearchive_respects_kind() -> None:
    """Regression: dearchive branch always defaulted to kind='expense', hiding archived income categories."""
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        await db.connect()
        await db.ensure_user(111)
        budget_id = await db.create_budget(111)

        expense_cats = await db.list_active_categories(budget_id, "expense")
        income_cats = await db.list_active_categories(budget_id, "income")
        await db.archive_category(expense_cats[0]["category_id"])   # Продукты
        await db.archive_category(income_cats[0]["category_id"])    # Зарплата

        callback = FakeCallbackQuery()
        await render_categories_screen(callback, db, budget_id, "dearchive", 1, "income")

        markup = callback.message.edit_text.await_args.kwargs["reply_markup"]
        names = {btn.text for row in markup.inline_keyboard for btn in row}
        assert "Зарплата" in names
        assert "Продукты" not in names

        await db.close()


async def test_new_income_category_sort_order_is_income_scoped() -> None:
    """Regression: new category sort_order was computed from expense max even for income categories."""
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        await db.connect()
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

        await db.close()
        print("categories ✓")

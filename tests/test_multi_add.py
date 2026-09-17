import tempfile
from pathlib import Path

from callback import CategoryCB, NavCB
from db import Database
from handlers.expenses import add_again, amount_entered, category_chosen
from tests.fakes import FakeCallbackQuery, FakeMessage, make_state, unpack_callback_data


async def test_amount_entered_keeps_date_and_offers_add_again() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        async with Database(Path(tmp) / "test.db") as db:
            await db.ensure_user(111)
            budget_id = await db.create_budget(111)
            cat_id = (await db.list_active_categories(budget_id, "expense"))[0]["category_id"]

            state = make_state()
            await state.update_data(mode="today", kind="expense", category_id=cat_id)
            message = FakeMessage(text="100", user_id=111)

            await amount_entered(message, state, db, budget_id, "Europe/Chisinau")

            data = await state.get_data()
            assert data["mode"] == "today"    # дата/режим сохранены, а не сброшены
            assert "category_id" not in data  # но выбор категории/суммы — не переносится

            markup = message.answer.await_args.kwargs["reply_markup"]
            btn_cb = unpack_callback_data(markup, 0, 0, NavCB)
            assert btn_cb == NavCB(to="add_again", kind="expense")


async def test_add_again_skips_date_prompt_and_reuses_same_date() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        async with Database(Path(tmp) / "test.db") as db:
            await db.ensure_user(111)
            budget_id = await db.create_budget(111)
            cats = await db.list_active_categories(budget_id, "expense")

            state = make_state()
            await state.update_data(mode="today", kind="expense", category_id=cats[0]["category_id"])
            message1 = FakeMessage(text="100", user_id=111)
            await amount_entered(message1, state, db, budget_id, "Europe/Chisinau")

            # "Добавить ещё на эту дату" -> напрямую к выбору категории, без повторного запроса даты
            callback = FakeCallbackQuery(user_id=111)
            await add_again(callback, state, db, NavCB(to="add_again", kind="expense"), budget_id)
            callback.message.edit_text.assert_awaited_once()  # экран категорий, не запрос даты

            cat_cb = CategoryCB(id=cats[1]["category_id"], purpose="expense", kind="expense")
            await category_chosen(callback, cat_cb, state)

            message2 = FakeMessage(text="50", user_id=111)
            await amount_entered(message2, state, db, budget_id, "Europe/Chisinau")

            rows = await db.list_recent_transactions(budget_id, limit=10, offset=0)
            assert len(rows) == 2
            assert rows[0]["date"] == rows[1]["date"]  # одна и та же дата у обоих добавлений


async def test_add_again_falls_back_to_menu_on_stale_state() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        async with Database(Path(tmp) / "test.db") as db:
            await db.ensure_user(111)
            budget_id = await db.create_budget(111)

            state = make_state()  # пустой state — сессия "устарела"
            callback = FakeCallbackQuery(user_id=111)

            await add_again(callback, state, db, NavCB(to="add_again", kind="expense"), budget_id)

            callback.message.edit_text.assert_awaited_once()

            print("multi_add ✓")

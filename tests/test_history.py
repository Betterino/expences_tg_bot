import tempfile
from pathlib import Path

from callback import NavCB
from db import Database
from handlers.history import render_history_screen
from tests.fakes import FakeCallbackQuery, unpack_callback_data


async def test_list_recent_transactions_ordering_and_fallbacks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        async with Database(Path(tmp) / "test.db") as db:
            await db.ensure_user(111)
            await db.ensure_user(222)
            await db.set_nickname(111, "Вася")
            budget_id = await db.create_budget(111)
            await db.add_to_budget(222, budget_id)

            expense_cats = await db.list_active_categories(budget_id, "expense")
            income_cats = await db.list_active_categories(budget_id, "income")
            cat_id = expense_cats[0]["category_id"]

            await db.add_expense(budget_id, 111, cat_id, 10000, "2026-01-01", "expense")   # Вася
            await db.add_expense(budget_id, 222, cat_id, 20000, "2026-01-02", "expense")   # без никнейма
            await db.add_expense(budget_id, 111, income_cats[0]["category_id"], 30000, "2026-01-03", "income")

            # категория удалена -> должна показываться как "Без категории", а не падать
            await db.delete_category(cat_id)

            rows = await db.list_recent_transactions(budget_id, limit=10, offset=0)
            assert len(rows) == 3
            assert rows[0]["date"] == "2026-01-03"  # самая новая запись первая (ORDER BY expense_id DESC)
            assert rows[0]["nickname"] == "Вася"
            assert rows[1]["category_name"] == "Без категории"  # категория удалена (запись от 222)
            assert rows[1]["nickname"] == ""  # у 222 никнейм не задан -> fallback в handlers/history.py
            assert rows[2]["category_name"] == "Без категории"  # категория удалена (запись от 111)
            assert rows[2]["nickname"] == "Вася"

            assert await db.count_transactions(budget_id) == 3
            assert await db.count_transactions(budget_id, "income") == 1
            assert await db.count_transactions(budget_id, "expense") == 2

            # LIMIT/OFFSET
            page1 = await db.list_recent_transactions(budget_id, limit=2, offset=0)
            page2 = await db.list_recent_transactions(budget_id, limit=2, offset=2)
            assert len(page1) == 2 and len(page2) == 1

            print("history ✓")


async def test_render_history_screen_shows_id_fallback_and_pagination() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        async with Database(Path(tmp) / "test.db") as db:
            await db.ensure_user(111)
            budget_id = await db.create_budget(111)
            cat_id = (await db.list_active_categories(budget_id, "expense"))[0]["category_id"]
            await db.add_expense(budget_id, 111, cat_id, 5000, "2026-02-01", "expense")

            callback = FakeCallbackQuery()
            await render_history_screen(callback, db, budget_id, page=1)

            text = callback.message.edit_text.await_args.kwargs["text"]
            assert "ID 111" in text  # нет никнейма -> fallback на ID

            # только 1 запись -> одна страница -> кнопок пагинации нет, только "Меню"
            markup = callback.message.edit_text.await_args.kwargs["reply_markup"]
            assert len(markup.inline_keyboard) == 1
            assert unpack_callback_data(markup, 0, 0, NavCB) == NavCB(to="menu")

            print("history-screen ✓")

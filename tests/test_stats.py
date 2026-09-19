import tempfile
from pathlib import Path

import richtext
from db import Database
from handlers.stats import input_year
from tests.fakes import FakeMessage, make_state, rich_blocks


async def test_input_year_includes_both_totals() -> None:
    """Regression test for the stats screen being built from only 4 of 6 required args."""
    with tempfile.TemporaryDirectory() as tmp:
        async with Database(Path(tmp) / "test.db") as db:
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

            print("stats ✓")

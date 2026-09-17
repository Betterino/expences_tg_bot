import tempfile
from pathlib import Path

from db import Database
from handlers.onboard import JoinBudget, join_code_budget
from tests.fakes import FakeMessage, make_state


async def test_invalid_code_replies_without_editing() -> None:
    """Regression test: message.edit_text() on the user's own message raised an unhandled
    Telegram API error (bots can't edit messages they didn't send)."""
    with tempfile.TemporaryDirectory() as tmp:
        async with Database(Path(tmp) / "test.db") as db:
            user = await db.ensure_user(111)

            state = make_state()
            await state.set_state(JoinBudget.waiting_code)
            message = FakeMessage(text="bogus-code")

            await join_code_budget(message, db, state, user)

            message.answer.assert_awaited_once_with("Такого бюджета нет")
            message.edit_text.assert_not_awaited()
            assert await state.get_state() == JoinBudget.waiting_code.state  # untouched on failure


async def test_successful_join_clears_state() -> None:
    """Regression test: success path never called state.clear(), leaving JoinBudget.waiting_code
    active so the user's next message was misrouted as another invite code attempt."""
    with tempfile.TemporaryDirectory() as tmp:
        async with Database(Path(tmp) / "test.db") as db:
            await db.ensure_user(111)
            budget_id = await db.create_budget(111)
            code = await db.get_invite_code(budget_id)

            joiner = await db.ensure_user(222)
            state = make_state(user_id=222)
            await state.set_state(JoinBudget.waiting_code)
            message = FakeMessage(text=code, user_id=222)

            await join_code_budget(message, db, state, joiner)

            assert await state.get_state() is None
            joiner_after = await db.ensure_user(222)
            assert joiner_after["current_budget"] == budget_id

            print("onboard ✓")

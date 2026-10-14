
from db import Database
from handlers.onboard import JoinBudget, join_code_budget, rotate_code
from tests.fakes import FakeCallbackQuery, FakeMessage, make_state
from texts import Onboarding


async def test_invalid_code_replies_without_editing(db: Database) -> None:
    """Regression test: message.edit_text() on the user's own message raised an unhandled
    Telegram API error (bots can't edit messages they didn't send)."""
    user = await db.ensure_user(111)

    state = make_state()
    await state.set_state(JoinBudget.waiting_code)
    message = FakeMessage(text="bogus-code")

    await join_code_budget(message, db, state, user)

    message.answer.assert_awaited_once_with(Onboarding.NO_SUCH_BUDGET)
    message.edit_text.assert_not_awaited()
    assert await state.get_state() == JoinBudget.waiting_code.state  # untouched on failure


async def test_join_code_rejects_non_text(db: Database) -> None:
    """BUG-5: a sticker/photo at the invite-code prompt gives message.text=None --
    join_code_budget used to call None.strip() and raise AttributeError."""
    user = await db.ensure_user(111)

    state = make_state()
    await state.set_state(JoinBudget.waiting_code)
    message = FakeMessage(text=None)

    await join_code_budget(message, db, state, user)

    message.answer.assert_awaited_once_with(Onboarding.NO_SUCH_BUDGET)
    assert await state.get_state() == JoinBudget.waiting_code.state


async def test_rotate_code_invalidates_old_code(db: Database) -> None:
    """SEC-4: a leaked invite code is permanent otherwise -- anyone who ever saw it
    could join the budget forever. Rotating must invalidate the old code."""
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)
    old_code = await db.get_invite_code(budget_id)

    callback = FakeCallbackQuery()
    await rotate_code(callback, db, budget_id)

    new_code = await db.get_invite_code(budget_id)
    assert new_code != old_code
    assert await db.check_invite_code(old_code) is None
    text = callback.message.edit_text.await_args.kwargs["text"]
    assert new_code in text


async def test_successful_join_clears_state(db: Database) -> None:
    """Regression test: success path never called state.clear(), leaving JoinBudget.waiting_code
    active so the user's next message was misrouted as another invite code attempt."""
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

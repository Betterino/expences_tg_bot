"""Full-stack routing tests: feed a real event through the actual Dispatcher/router chain
(handlers.routers, in the exact order bot.py registers them) to catch handlers being shadowed
by an earlier router's catch-all — a class of bug that calling handler functions directly
(as the other tests/test_*.py files do) cannot catch.

Regression: handlers/edit.py has an unconditional `@router.callback_query()` catch-all
("unhandled"). If any router with its own real handlers is registered after edit.router in
handlers.routers, every one of its callback_query handlers becomes unreachable — edit's
catch-all always matches first and stops propagation.
"""
import tempfile
from pathlib import Path

from aiogram import Dispatcher
from aiogram.types import CallbackQuery, Chat, Message, User

from db import Database
from handlers import routers


class _FakeState:
    async def get_state(self):
        return None

    async def get_data(self):
        return {}


def _make_callback_query(data: str) -> CallbackQuery:
    user = User(id=111, is_bot=False, first_name="t")
    chat = Chat(id=1, type="private")
    msg = Message(message_id=1, date=0, chat=chat)
    return CallbackQuery(id="1", from_user=user, chat_instance="x", data=data, message=msg)


async def test_history_button_is_not_swallowed_by_edits_catch_all() -> None:
    """Regression: 'История' (nav:history) must reach handlers/history.py, not edit.py's
    unconditional catch-all — this only happens if history.router is registered before
    edit.router in handlers.routers."""
    with tempfile.TemporaryDirectory() as tmp:
        async with Database(Path(tmp) / "test.db") as db:
            await db.ensure_user(111)
            budget_id = await db.create_budget(111)

            dp = Dispatcher()
            for r in routers:
                dp.include_router(r)

            import traceback

            cb = _make_callback_query("nav:history:expense")
            tb_text = ""
            try:
                await dp.propagate_event(
                    "callback_query", cb, db=db, budget_id=budget_id, state=_FakeState(), user={"user_id": 111}
                )
            except RuntimeError as e:
                # message.edit_text()/answer() fails outside a real Bot context — expected here.
                # The traceback's origin is what actually proves which handler ran.
                assert "mount" in str(e), e
                tb_text = traceback.format_exc()
            else:
                raise AssertionError("expected a RuntimeError from calling edit_text without a live Bot")

            assert "handlers/history.py" in tb_text, tb_text

            print("routing ✓")

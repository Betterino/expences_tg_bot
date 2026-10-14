"""Full-stack routing tests: feed a real event through the actual Dispatcher/router chain
(handlers.routers, in the exact order bot.py registers them) to catch handlers being shadowed
by an earlier router's catch-all — a class of bug that calling handler functions directly
(as the other tests/test_*.py files do) cannot catch.

Regression: handlers/fallback.py has an unconditional `@router.callback_query()` catch-all
("unhandled"). If any router with its own real handlers is registered after fallback.router in
handlers.routers, every one of its callback_query handlers becomes unreachable — the
catch-all always matches first and stops propagation.
"""
from aiogram import Dispatcher

from callback import NavCB
from db import Database
from handlers import routers
from tests.fakes import dispatch_traceback


async def test_history_button_is_not_swallowed_by_edits_catch_all(
    db: Database, dispatcher: Dispatcher
) -> None:
    """Regression: 'История' (nav:history) must reach handlers/history.py, not edit.py's
    unconditional catch-all — this only happens if history.router is registered before
    edit.router in handlers.routers."""
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)

    # Packed from the class, not hand-written -- a hardcoded "nav:history:expense" went
    # stale (no handler matched) the moment NavCB grew a `mode` field.
    tb_text = await dispatch_traceback(
        dispatcher, NavCB(to="history").pack(), 111, db=db, budget_id=budget_id
    )
    assert "handlers/history.py" in tb_text, tb_text


def test_fallback_router_is_mounted_last() -> None:
    assert routers[-1].name == "fallback"

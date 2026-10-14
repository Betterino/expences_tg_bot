"""PAT-1: every callback_query gets answered exactly once via CallbackAnswerMiddleware,
which the dispatcher injects as the `callback_answer` kwarg and auto-answers in a
`finally` block unless a handler already marked it answered (setting `.text`).

A handler that calls `callback.answer(...)` directly instead of going through the
injected `callback_answer` object doesn't mark CallbackAnswer.answered -- so the
middleware's `finally` block answers *again*, and Telegram rejects answering the same
callback query twice. That's checked statically here rather than through a live
Dispatcher: without a real Bot, message.edit_text()/answer() inside a handler raises
before ever reaching a callback.answer() call (see tests/test_routing.py), so a
full-stack dispatch test can't observe the double-answer either way.
"""
from pathlib import Path

from handlers import routers

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_callback_answer_middleware_is_attached() -> None:
    source = (REPO_ROOT / "bot.py").read_text(encoding="utf-8")
    assert "dp.callback_query.middleware(CallbackAnswerMiddleware())" in source


def test_no_production_handler_calls_callback_answer_directly() -> None:
    """sandbox/ is explicitly exempt -- its handlers predate PAT-1 and the plan for
    this pass says to leave the sandbox alone."""
    handlers_dir = REPO_ROOT / "handlers"
    for path in handlers_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "callback.answer(" not in text, path


def test_fallback_router_is_mounted_last() -> None:
    """Reasserted here (also covered in tests/test_routing.py): fallback.router's
    unconditional @router.callback_query() catch-all would swallow every later
    router's handlers, so nothing may register after it."""
    assert routers[-1].name == "fallback"

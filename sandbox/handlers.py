"""The only aiogram-aware module in the sandbox. Contains no formatting logic.

Registered in handlers/__init__.py *before* edit.router: handlers/edit.py:186 declares
@router.callback_query() with no filter, and aiogram stops propagation at the first
router that has a matching handler -- so nothing registered after it ever sees a
callback query.

No middleware setup is needed here. ContextMiddleware is attached to the dispatcher's
observer (dp.callback_query.middleware(...) in bot.py:78), not to any single router,
so db/budget_id/tz arrive as kwargs for every router included in that dispatcher.
Being *inner* middleware it only runs once a filter has already matched, which means
callbacks the sandbox does not claim never pay for its ensure_user round-trip.
"""
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InputRichBlockParagraph, InputRichMessage

from callback import NavCB
from db import Database
from sandbox import TableData
from sandbox.callback import SandboxCB
from sandbox.fixtures import FIXTURES
from sandbox.keyboard import sandbox_kb
from sandbox.texts import Sandbox as SandboxTexts
from sandbox.variants import VARIANTS, Body, get, render
from utils import stats_bounds, today

router = Router(name="sandbox")

MESSAGE_LIMIT = 4096
RICH_LIMIT = 32768


def _rich_text_len(blocks: list) -> int:
    """Summed length of every literal text found in a rich block tree.

    Walks the handful of fields that can carry text or nested blocks (table cells are
    a list of lists, list items and details wrap further blocks) instead of assuming
    a fixed shape, since the tree differs between "rtable" and "rdoc".
    """
    total = 0

    def walk(obj) -> None:
        nonlocal total
        if isinstance(obj, str):
            total += len(obj)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
        elif hasattr(obj, "model_dump"):
            for attr in ("text", "blocks", "cells", "items", "caption", "summary"):
                value = getattr(obj, attr, None)
                if value is not None:
                    walk(value)

    walk(blocks)
    return total


async def live_data(db: Database, budget_id: int, tz: str) -> TableData:
    """Read-only snapshot of the current month, via the existing stats queries.

    Uses utils.today(tz) rather than date.today(): handlers/stats.py:44 still reads the
    server's clock even though ContextMiddleware injects the user's timezone, so around
    month boundaries it can pick the wrong month. Separate fix, not this branch.
    """
    now = today(tz)
    start, end = stats_bounds(now.year, now.month, now.year, now.month)
    return TableData(
        start=start,
        end=end,
        total_e=await db.stats_total(budget_id, start, end, "expense"),
        expense=await db.expense_by_category(budget_id, start, end),
        income=await db.income_by_category(budget_id, start, end),
        total_i=await db.stats_total(budget_id, start, end, "income"),
    )


async def resolve(source: str, db, budget_id, tz) -> tuple[TableData, str, str | None]:
    """-> (data, effective source, toast to show). Fixtures never touch the DB."""
    if source != "live":
        return FIXTURES.get(source, FIXTURES["demo"]), source, None
    if budget_id is None:
        return FIXTURES["demo"], "demo", SandboxTexts.NO_BUDGET
    return await live_data(db, budget_id, tz), "live", None


def build_screen(key: str, source: str, data: TableData) -> tuple[Body, str | None]:
    """-> (message body, toast). The size counter is the teaching device: you watch
    «Рамки» cost 850 characters and «Без моноширинного» 1400 for identical data --
    rich variants get the same treatment against RICH_LIMIT instead of MESSAGE_LIMIT."""
    body = render(key, data)
    toast = None
    if isinstance(body, str):
        header = SandboxTexts.HEADER.format(
            label=get(key).label, source=SandboxTexts.SOURCE_LABELS[source], size=len(body)
        )
        if len(header) + len(body) > MESSAGE_LIMIT:
            body = body[: MESSAGE_LIMIT - len(header) - 1]
            toast = SandboxTexts.TOO_LONG
        return header + body, toast

    blocks = list(body.blocks or [])
    size = _rich_text_len(blocks)
    header_text = SandboxTexts.RICH_HEADER.format(
        label=get(key).label, source=SandboxTexts.SOURCE_LABELS[source], size=size
    )
    if size > RICH_LIMIT:
        toast = SandboxTexts.TOO_LONG
    return InputRichMessage(blocks=[InputRichBlockParagraph(text=header_text), *blocks]), toast


async def show(callback: CallbackQuery, key: str, source: str, db, budget_id, tz) -> None:
    data, source, toast = await resolve(source, db, budget_id, tz)
    body, size_toast = build_screen(key, source, data)
    markup = sandbox_kb(key, source)
    try:
        if isinstance(body, str):
            await callback.message.edit_text(text=body, reply_markup=markup)
        else:
            await callback.message.edit_text(rich_message=body, reply_markup=markup)
    except TelegramBadRequest as error:
        # Telegram rejects an editMessageText whose text AND markup are byte-identical
        # to what is already on screen -- which is exactly what re-tapping the selected
        # variant produces. Unhandled it reaches @dp.error() and shows the user
        # "Что-то сломалось" for a no-op. Swallow *this* 400 only, re-raise every other.
        if "message is not modified" in str(error):
            pass
        elif not isinstance(body, str):
            # aiogram knowing the 10.2 schema does not guarantee the Bot API server or
            # this chat actually accepts send_rich_message -- fall back to the plain
            # "Как сейчас" variant rather than letting the error reach @dp.error().
            fallback_body, _ = build_screen("base", source, data)
            await callback.message.edit_text(text=fallback_body, reply_markup=sandbox_kb("base", source))
            await callback.answer(SandboxTexts.RICH_UNAVAILABLE)
            return
        else:
            raise
    # Telegram spins the button's loading indicator for ~30s until the callback query is
    # answered, so every path -- including the swallowed one above -- must reach this.
    await callback.answer(toast or size_toast)


@router.callback_query(NavCB.filter(F.to == "sandbox"))
async def open_sandbox(callback: CallbackQuery, db: Database, budget_id, tz):
    await show(callback, VARIANTS[0].key, "demo", db, budget_id, tz)


@router.callback_query(SandboxCB.filter(F.action == "show"))
async def show_variant(callback: CallbackQuery, callback_data: SandboxCB, db: Database, budget_id, tz):
    await show(callback, callback_data.key, callback_data.source, db, budget_id, tz)


@router.callback_query(SandboxCB.filter(F.action == "copy"))
async def send_copy(callback: CallbackQuery, callback_data: SandboxCB, db: Database, budget_id, tz):
    """Post the current render as a NEW message instead of editing in place, so several
    variants stack in the chat and can be scrolled side by side on a real phone. That is
    the only honest way to judge whether a wide table wraps."""
    data, source, toast = await resolve(callback_data.source, db, budget_id, tz)
    body, _ = build_screen(callback_data.key, source, data)
    if isinstance(body, str):
        await callback.message.answer(body)
    else:
        await callback.message.answer_rich(rich_message=body)
    await callback.answer(toast or SandboxTexts.COPIED)

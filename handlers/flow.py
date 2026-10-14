"""Guarded reads of FSM data for multi-step flows.

FSM *data* written by one update and read by a later one can be gone by the time the
reader runs: every "Меню" tap does state.clear(), and Telegram never removes the old
keyboards above it, so a stale button can arrive after the clear. A bare data["key"] then
raises KeyError, which surfaces as "Что-то сломалось"
(postmortems/2026-10-05-add-expense-mode-keyerror.md).

Where the next step is a *tap*, prefer carrying the value on the button itself
(CategoryCB.mode, the delete/rename confirm buttons' CategoryCB.id) -- then there is
nothing to lose. Where the next step is a *typed message* (amount, date, name, maximum),
a message carries no callback data, so FSM is unavoidable there; read it through
require_flow. tests/test_fsm_discipline.py rejects any data["key"] on a raw get_data().

No router here on purpose -- this module is a helper, not a handler set.
"""
import logging

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.callback_answer import CallbackAnswer

from texts import Errors

from .screens import show_menu

logger = logging.getLogger(__name__)


async def require_flow(
    state: FSMContext,
    event: Message | CallbackQuery,
    *keys: str,
    callback_answer: CallbackAnswer | None = None,
) -> dict | None:
    """FSM data read that treats a missing key as an expired flow, not a crash.

    Returns the data dict, or None after already telling the user and showing the menu.
    "Missing" is `is None`, not `not in` (amount_entered stores my_date=None outright)
    and not truthiness (changemax_category stores mode="").

    callback_answer: pass the handler's own (CallbackAnswerMiddleware injects it) --
    the middleware answers the query after the handler returns, so a direct
    answer() on the query here would be a second one and get a 400 from Telegram.
    """
    data = await state.get_data()
    missing = [k for k in keys if data.get(k) is None]
    if not missing:
        return data

    logger.warning("поток устарел: нет %s, state=%s", missing, await state.get_state())
    await state.clear()
    if isinstance(event, CallbackQuery):
        if callback_answer is not None:
            callback_answer.text = Errors.FLOW_EXPIRED
        await show_menu(event.message, edit=True)
    else:
        await event.answer(Errors.FLOW_EXPIRED)
        await show_menu(event, edit=False)
    return None

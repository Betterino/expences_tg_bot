import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.callback_answer import CallbackAnswer

from texts import Errors

from .screens import show_menu

logger = logging.getLogger(__name__)

router = Router(name="fallback")


@router.callback_query()
async def unhandled(callback: CallbackQuery, state: FSMContext, callback_answer: CallbackAnswer):
    logger.warning(
        "НЕ ПОЙМАН callback=%s state=%s user=%s",
        callback.data, await state.get_state(), callback.from_user.id,
    )
    # Mostly buttons from before a CallbackData format change (NavCB.mode in 1.5.1):
    # they still sit in users' chats and match nothing. A toast instead of silence --
    # the screen itself is left alone, the user may still want to read it.
    callback_answer.text = Errors.STALE_BUTTON


@router.message()
async def unhandled_message(message: Message, state: FSMContext):
    # Text typed outside any flow (no FSM state waits for it). Every waiting state has its
    # own handler on an earlier router, so this only sees messages nobody asked for.
    logger.warning("НЕ ПОЙМАНО сообщение state=%s user=%s", await state.get_state(), message.from_user.id)
    await show_menu(message, edit=False)

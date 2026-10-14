"""Test doubles for calling aiogram handlers directly, without a live Bot/Dispatcher.

Handlers in this project are plain async functions that receive injected objects
(message/callback/state/db/...). FakeMessage/FakeCallbackQuery record what they were
called with; make_state() is a real FSMContext backed by MemoryStorage, so state
transitions (set_state/get_data/update_data/clear) behave exactly as in production.
"""
import traceback
from unittest.mock import AsyncMock

from aiogram import Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, User
from aiogram.utils.callback_answer import CallbackAnswer


def make_state(bot_id: int = 1, chat_id: int = 1, user_id: int = 1) -> FSMContext:
    storage = MemoryStorage()
    key = StorageKey(bot_id=bot_id, chat_id=chat_id, user_id=user_id)
    return FSMContext(storage=storage, key=key)


def make_callback_answer() -> CallbackAnswer:
    """The real aiogram class, not a mock -- CallbackAnswerMiddleware hands handlers
    exactly this object (via the `callback_answer` param name), so tests calling
    handlers directly need the same `.text` setter contract it exposes."""
    return CallbackAnswer(answered=False)


class FakeUser:
    def __init__(self, user_id: int = 1):
        self.id = user_id


class FakeMessage:
    def __init__(self, text: str | None = None, user_id: int = 1):
        self.text = text
        self.from_user = FakeUser(user_id)
        self.answer = AsyncMock()
        self.answer_rich = AsyncMock()
        self.edit_text = AsyncMock()


_DEFAULT = object()


class FakeCallbackQuery:
    # isinstance(fake, CallbackQuery) is True, so handlers/flow.require_flow takes its
    # callback branch. isinstance() falls back to obj.__class__ -- the same trick
    # unittest.mock's Mock(spec=CallbackQuery) uses. type(fake) is still FakeCallbackQuery.
    @property
    def __class__(self):
        return CallbackQuery

    def __init__(self, user_id: int = 1, data: str | None = None, message=_DEFAULT):
        self.data = data
        self.from_user = FakeUser(user_id)
        # message=None mimics an inline-mode button; an InaccessibleMessage, a deleted one.
        # A sentinel rather than None as the default, because None is itself a value to test.
        self.message = FakeMessage(user_id=user_id) if message is _DEFAULT else message
        self.answer = AsyncMock()


def unpack_callback_data(markup, row: int, col: int, cb_cls):
    """Unpack the CallbackData at [row][col] of an InlineKeyboardMarkup into cb_cls."""
    button = markup.inline_keyboard[row][col]
    return cb_cls.unpack(button.callback_data)


def find_button(markup, text_contains: str):
    """Find the first button whose text contains text_contains, or None."""
    for row in markup.inline_keyboard:
        for button in row:
            if text_contains in button.text:
                return button
    return None


def rich_blocks(mock: AsyncMock) -> list:
    """Pull the block list out of the rich_message kwarg of a mock's last call.

    edit_rich/answer_rich (handlers/screens.py) always pass rich_message=<InputRichMessage>,
    never text= -- so tests assert against blocks instead of a formatted string.
    """
    rich_message = mock.await_args.kwargs["rich_message"]
    return list(rich_message.blocks or [])


class EmptyState:
    """Just enough of FSMContext for StateFilter to see "no state set" during a full
    Dispatcher propagation (tests/test_routing.py, tests/test_sandbox.py)."""

    async def get_state(self):
        return None

    async def get_data(self):
        return {}


async def dispatch_traceback(dp: Dispatcher, data: str, user_id: int, **kwargs) -> str:
    """Push a *real* CallbackQuery with callback_data=data through the whole router chain
    and return the traceback it dies with.

    Without a live Bot, the first edit_text()/answer() a handler makes raises
    RuntimeError("... not mounted to a any bot instance"). That failure is the point: the
    traceback names the file of whichever handler actually won the routing."""
    callback = CallbackQuery(
        id="1",
        from_user=User(id=user_id, is_bot=False, first_name="t"),
        chat_instance="x",
        data=data,
        message=Message(message_id=1, date=0, chat=Chat(id=1, type="private")),
    )
    try:
        await dp.propagate_event(
            "callback_query", callback, state=EmptyState(), user={"user_id": user_id}, **kwargs
        )
    except RuntimeError as error:
        assert "mount" in str(error), error
        return traceback.format_exc()
    raise AssertionError("ожидали RuntimeError от edit_text без живого Bot")

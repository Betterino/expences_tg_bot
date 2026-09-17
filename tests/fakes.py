"""Test doubles for calling aiogram handlers directly, without a live Bot/Dispatcher.

Handlers in this project are plain async functions that receive injected objects
(message/callback/state/db/...). FakeMessage/FakeCallbackQuery record what they were
called with; make_state() is a real FSMContext backed by MemoryStorage, so state
transitions (set_state/get_data/update_data/clear) behave exactly as in production.
"""
from unittest.mock import AsyncMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage


def make_state(bot_id: int = 1, chat_id: int = 1, user_id: int = 1) -> FSMContext:
    storage = MemoryStorage()
    key = StorageKey(bot_id=bot_id, chat_id=chat_id, user_id=user_id)
    return FSMContext(storage=storage, key=key)


class FakeUser:
    def __init__(self, user_id: int = 1):
        self.id = user_id


class FakeMessage:
    def __init__(self, text: str | None = None, user_id: int = 1):
        self.text = text
        self.from_user = FakeUser(user_id)
        self.answer = AsyncMock()
        self.edit_text = AsyncMock()


class FakeCallbackQuery:
    def __init__(self, user_id: int = 1, data: str | None = None):
        self.data = data
        self.from_user = FakeUser(user_id)
        self.message = FakeMessage(user_id=user_id)
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

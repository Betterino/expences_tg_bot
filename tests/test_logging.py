"""describe_update() is the one line logged for every in/out update (bot.py's
LoggingMiddleware) and fed to @dp.error() on crashes. These tests pin its format
against real aiogram Update objects so a refactor can't silently drop the user/payload."""
from aiogram.types import CallbackQuery, Chat, Message, Update, User

from logging_utils import describe_update, MAX_TEXT_LEN


def _message_update(text: str, update_id: int = 1) -> Update:
    user = User(id=111, is_bot=False, first_name="t", username="vasya")
    chat = Chat(id=222, type="private")
    msg = Message(message_id=1, date=0, chat=chat, from_user=user, text=text)
    return Update(update_id=update_id, message=msg)


def _callback_update(data: str, update_id: int = 2) -> Update:
    user = User(id=111, is_bot=False, first_name="t", username="vasya")
    chat = Chat(id=222, type="private")
    msg = Message(message_id=1, date=0, chat=chat)
    cb = CallbackQuery(id="1", from_user=user, chat_instance="x", data=data, message=msg)
    return Update(update_id=update_id, callback_query=cb)


def test_message_update_contains_user_and_text() -> None:
    line = describe_update(_message_update("150 продукты"))
    assert "111" in line
    assert "vasya" in line
    assert "150 продукты" in line


def test_callback_update_contains_user_and_data() -> None:
    line = describe_update(_callback_update("nav:menu"))
    assert "111" in line
    assert "nav:menu" in line


def test_long_text_is_truncated() -> None:
    long_text = "a" * (MAX_TEXT_LEN + 50)
    line = describe_update(_message_update(long_text))
    assert "a" * (MAX_TEXT_LEN + 50) not in line
    assert "a" * MAX_TEXT_LEN in line
    print("logging ✓")

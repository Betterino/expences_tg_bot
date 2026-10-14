"""describe_update() is the one line logged for every in/out update (bot.py's
LoggingMiddleware) and fed to @dp.error() on crashes. These tests pin its format
against real aiogram Update objects so a refactor can't silently drop the user/payload."""
import logging
import tempfile
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from aiogram.types import CallbackQuery, Chat, Message, Update, User

from logging_utils import MAX_TEXT_LEN, describe_update, setup_logging


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


def test_message_update_hides_text_by_default() -> None:
    """SEC-5: message bodies are personal data -- only their length is logged
    unless the caller opts in via log_text=True (LOG_MESSAGE_TEXT=1 in bot.py)."""
    line = describe_update(_message_update("150 продукты"))
    assert "111" in line
    assert "vasya" in line
    assert "150 продукты" not in line
    assert "text_len=12" in line


def test_message_update_contains_text_when_opted_in() -> None:
    line = describe_update(_message_update("150 продукты"), log_text=True)
    assert "150 продукты" in line


def test_callback_update_contains_user_and_data() -> None:
    line = describe_update(_callback_update("nav:menu"))
    assert "111" in line
    assert "nav:menu" in line


def test_long_text_is_truncated_when_opted_in() -> None:
    long_text = "a" * (MAX_TEXT_LEN + 50)
    line = describe_update(_message_update(long_text), log_text=True)
    assert "a" * (MAX_TEXT_LEN + 50) not in line
    assert "a" * MAX_TEXT_LEN in line


def _with_logging(check) -> None:
    """setup_logging() reconfigures the *process-wide* root logger (basicConfig(force=True)),
    so every test using it must hand the old handlers back -- otherwise later tests in
    the same run would log into a deleted tempdir."""
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    aiogram_event = logging.getLogger("aiogram.event")
    saved_event_level = aiogram_event.level
    with tempfile.TemporaryDirectory() as tmp:
        try:
            check(Path(tmp), setup_logging(Path(tmp) / "logs"))
        finally:
            for handler in root.handlers:
                handler.close()  # the file handle, before TemporaryDirectory deletes the dir
            root.handlers[:] = saved_handlers
            root.setLevel(saved_level)
            aiogram_event.setLevel(saved_event_level)


def test_log_file_round_trips_russian_text() -> None:
    def check(tmp: Path, log_file: Path) -> None:
        logging.getLogger("test").warning("поток устарел: нет ['my_date']")
        for handler in logging.getLogger().handlers:
            handler.flush()
        assert "поток устарел: нет ['my_date']" in log_file.read_text(encoding="utf-8")

    _with_logging(check)


def test_rollover_keeps_three_days() -> None:
    """keep_days=3 = today's bot.log + 2 rotated files. Stdlib prunes by the
    "bot.log.YYYY-MM-DD" suffix, which is why logging_utils sets no custom namer."""
    def check(tmp: Path, log_file: Path) -> None:
        for day in range(1, 8):  # a week of leftovers from earlier runs
            (log_file.parent / f"bot.log.2026-10-0{day}").write_text("old", encoding="utf-8")
        handler = next(h for h in logging.getLogger().handlers if isinstance(h, TimedRotatingFileHandler))

        handler.doRollover()

        files = sorted(p.name for p in log_file.parent.iterdir())
        assert len(files) <= 3, files
        assert "bot.log" in files
        assert "bot.log.2026-10-01" not in files  # the oldest go first

    _with_logging(check)

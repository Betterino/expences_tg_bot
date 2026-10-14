import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from aiogram.types import Update

MAX_TEXT_LEN = 100
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_KEEP_DAYS = 3


def setup_logging(log_dir: Path, keep_days: int = LOG_KEEP_DAYS, level: int = logging.INFO) -> Path:
    """stderr + one file per day under log_dir, the last keep_days days kept.

    Rollover and pruning are both stdlib's: backupCount=keep_days-1 rotated files plus
    the live bot.log. No custom `namer` on purpose -- getFilesToDelete() finds old files
    by the "bot.log." prefix, so a prettier name would silently stop the pruning.
    force=True replaces the import-time basicConfig in bot.py.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "bot.log"
    file_handler = TimedRotatingFileHandler(
        log_file, when="midnight", backupCount=keep_days - 1, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.basicConfig(
        level=level, format=LOG_FORMAT, handlers=[logging.StreamHandler(), file_handler], force=True
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    return log_file


def describe_update(update: Update, log_text: bool = False) -> str:
    """One-line human-readable summary of an incoming update, for logging.

    Message bodies (amounts, category names, nicknames the user typed) are personal
    data -- they don't belong in plaintext stdout/log files by default (SEC-5). Only
    the length is logged unless LOG_MESSAGE_TEXT=1 opts back into the previous
    behavior for local debugging.
    """
    user = None
    if update.message is not None:
        user = update.message.from_user
    elif update.callback_query is not None:
        user = update.callback_query.from_user
    user_part = f"user={user.id} @{user.username}" if user else "user=?"

    if update.message is not None:
        chat_id = update.message.chat.id
        raw = update.message.text or ""
        payload = f"text={raw[:MAX_TEXT_LEN]!r}" if log_text else f"text_len={len(raw)}"
        return f"upd={update.update_id} msg  {user_part} chat={chat_id} {payload}"
    if update.callback_query is not None:
        chat_id = update.callback_query.message.chat.id if update.callback_query.message else "?"
        return f"upd={update.update_id} cb   {user_part} chat={chat_id} data={update.callback_query.data!r}"
    return f"upd={update.update_id} {update.event_type} {user_part}"

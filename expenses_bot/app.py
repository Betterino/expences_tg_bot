import asyncio
import logging
import time

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
from aiogram.types import ErrorEvent, Update, User
from aiogram.utils.callback_answer import CallbackAnswerMiddleware

from expenses_bot.config import API_KEY, DATA_DIR, LOG_MESSAGE_TEXT
from expenses_bot.db import Database, backup_loop
from expenses_bot.handlers import routers
from expenses_bot.logging_utils import describe_update, setup_logging
from expenses_bot.ui.texts import Errors

logger = logging.getLogger(__name__)

# One asyncio.Lock per (bot, chat, user): a user's updates queue instead of interleaving,
# so a "Меню" tap can no longer state.clear() in the middle of another update's flow
# (docs/postmortems/2026-10-05-add-expense-mode-keyerror.md). The default is a no-op lock.
dp = Dispatcher(storage=MemoryStorage(), events_isolation=SimpleEventIsolation())


class LoggingMiddleware(BaseMiddleware):
    """Registered after the Dispatcher's own FSM outer middleware, so it runs *inside*
    the per-user isolation lock: "→" is logged once the lock is acquired, a queued
    update shows up as a large "←" elapsed_ms, and completions can no longer arrive
    out of order for the same user."""

    async def __call__(self, handler, event: Update, data):
        logger.info("→ %s", describe_update(event, LOG_MESSAGE_TEXT))
        started = time.monotonic()
        try:
            return await handler(event, data)
        finally:
            elapsed_ms = (time.monotonic() - started) * 1000
            logger.info("← upd=%s %.0fms", event.update_id, elapsed_ms)


@dp.error()
async def on_error(event: ErrorEvent):
    logger.exception("ошибка при обработке: %s", describe_update(event.update, LOG_MESSAGE_TEXT))
    try:
        if event.update.callback_query is not None:
            await event.update.callback_query.answer(Errors.SOMETHING_BROKE, show_alert=True)
        elif event.update.message is not None:
            await event.update.message.answer(Errors.SOMETHING_BROKE)
    except Exception:
        logger.exception("не удалось уведомить пользователя об ошибке")

class ContextMiddleware(BaseMiddleware):
    def __init__(self, db: Database):
        self.db = db

    async def __call__(self, handler, event, data):
        tg_user: User | None = data.get("event_from_user")
        if tg_user is None:
            return None
        user = await self.db.ensure_user(tg_user.id)
        data["db"] = self.db
        data["user"] = user
        data["budget_id"] = user["current_budget"]
        data["tz"] = user["timezone"]
        data["nickname"] = user["nickname"]
        return await handler(event, data)


async def main():
    setup_logging(DATA_DIR / "logs")
    if API_KEY is None:
        raise RuntimeError("API_KEY не задан (переменная окружения или .env)")
    # Built here, not at import: importing the app (tests do) must not need a token.
    bot = Bot(API_KEY, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    db = Database(DATA_DIR / "expenses.db")
    await db.connect()
    task = asyncio.create_task(backup_loop(db, DATA_DIR / "backups"))
    dp.update.outer_middleware(LoggingMiddleware())
    middleware = ContextMiddleware(db)
    dp.message.middleware(middleware)
    dp.callback_query.middleware(middleware)
    dp.callback_query.middleware(CallbackAnswerMiddleware())
    for router in routers:
        dp.include_router(router)
    try:
        # start_polling() turns SIGTERM/SIGINT (`docker compose stop`, Ctrl+C) into a
        # graceful stop, so this finally still runs and the DB is closed cleanly.
        await dp.start_polling(bot)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await db.close()

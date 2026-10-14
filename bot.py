import asyncio
import logging
import sys
import time
from pathlib import Path

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
from aiogram.types import ErrorEvent, Update, User
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from dotenv import get_key

from db import Database, backup_loop
from handlers import routers
from logging_utils import LOG_FORMAT, describe_update, setup_logging
from preflight import SuiteFailed, run_tests
from texts import Errors

# stderr-only until main() calls setup_logging() -- kept so the API_KEY error below is visible.
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logging.getLogger("aiogram.event").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

key = get_key(".env","API_KEY")
if key is None:
    raise RuntimeError("API_KEY не задан в .env")
# Message bodies are personal data (SEC-5) -- off by default, opt in for local debugging.
LOG_MESSAGE_TEXT = get_key(".env", "LOG_MESSAGE_TEXT") == "1"
bot = Bot(key,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
# One asyncio.Lock per (bot, chat, user): a user's updates queue instead of interleaving,
# so a "Меню" tap can no longer state.clear() in the middle of another update's flow
# (postmortems/2026-10-05-add-expense-mode-keyerror.md). The default is a no-op lock.
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
    setup_logging(Path("data/logs"))
    db = Database(Path("data/expenses.db"))
    await db.connect()
    task = asyncio.create_task(backup_loop(db, Path("data/backups")))
    dp.update.outer_middleware(LoggingMiddleware())
    middleware = ContextMiddleware(db)
    dp.message.middleware(middleware)
    dp.callback_query.middleware(middleware)
    dp.callback_query.middleware(CallbackAnswerMiddleware())
    for router in routers:
        dp.include_router(router)
    try:
        await dp.start_polling(bot)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await db.close()


if __name__ == "__main__":
    # Red suite = no polling (preflight.py). --skip-tests is the emergency bypass, e.g.
    # to bring the bot back up while a known-flaky test is being fixed.
    if "--skip-tests" in sys.argv:
        logger.warning("тесты пропущены (--skip-tests)")
    else:
        logger.info("прогоняю тесты перед запуском...")
        try:
            logger.info("тесты пройдены: %s", run_tests())
        except SuiteFailed as failure:
            logger.error(
                "тесты не прошли (%s), бот не запущен. Отчёт: %s", failure.summary, failure.report.resolve()
            )
            sys.exit(1)
    asyncio.run(main())












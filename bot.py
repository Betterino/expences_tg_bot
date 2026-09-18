from dotenv import get_key
from aiogram import Bot,Dispatcher, BaseMiddleware
from aiogram.types import User, ErrorEvent, Update
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import asyncio
import time
from db import Database, backup_loop
from handlers import routers
from pathlib import Path
import logging
from logging_utils import describe_update
from texts import Errors

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logging.getLogger("aiogram.event").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

key = get_key(".env","API_KEY")
assert key is not None
bot = Bot(key,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())


class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data):
        logger.info("→ %s", describe_update(event))
        started = time.monotonic()
        try:
            return await handler(event, data)
        finally:
            elapsed_ms = (time.monotonic() - started) * 1000
            logger.info("← upd=%s %.0fms", event.update_id, elapsed_ms)


@dp.error()
async def on_error(event: ErrorEvent):
    logger.exception("ошибка при обработке: %s", describe_update(event.update))
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
        if data["budget_id"] is not None:
            data["budget_type"] = await self.db.get_budget_type(data["budget_id"])
        else:
            data["budget_type"] = None
        return await handler(event, data)
    

async def main():
    db = Database(Path("data/expenses.db"))
    await db.connect()
    task = asyncio.create_task(backup_loop(db, Path("data/backups")))
    dp.update.outer_middleware(LoggingMiddleware())
    middleware = ContextMiddleware(db)
    dp.message.middleware(middleware)
    dp.callback_query.middleware(middleware)
    for router in routers:
        dp.include_router(router)
    try:
        await dp.start_polling(bot)
    finally:
        task.cancel()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())












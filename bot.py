from dotenv import get_key
from aiogram import Bot,Dispatcher, BaseMiddleware
from aiogram.types import User, ErrorEvent
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import asyncio
from db import Database, backup_loop
from handlers import routers
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

key = get_key(".env","API_KEY")
assert key is not None
bot = Bot(key,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())



@dp.error()
async def on_error(event: ErrorEvent):
    logger.exception("ошибка при обработке %s", event.update.event_type)

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
        if data["budget_id"] is not None:
            data["budget_type"] = await self.db.get_budget_type(data["budget_id"])
        else:
            data["budget_type"] = None
        return await handler(event, data)
    

async def main():
    db = Database(Path("data/expenses.db"))
    await db.connect()
    task = asyncio.create_task(backup_loop(db, Path("data/backups")))
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












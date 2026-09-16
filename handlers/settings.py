from datetime import datetime
from callback import  TzCB,NavCB
from keyboards import  cancel_kb,timezone_kb,settings_kb

from aiogram import  F,Router

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from constants import TIMEZONES
from zoneinfo import ZoneInfo

from db import Database


from aiogram.types import Message, CallbackQuery




PER_PAGE = 6
router = Router(name="settings")

class Settings(StatesGroup):
    waiting_timezone = State()

@router.callback_query(NavCB.filter(F.to == "set"))
async def settings(callback: CallbackQuery, db: Database, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(text="Настройки",reply_markup=settings_kb())
    pass

@router.callback_query(NavCB.filter(F.to == "timez"))
async def timezones(callback: CallbackQuery, db: Database,user):
    now = datetime.now(ZoneInfo(user["timezone"])).strftime("%H:%M")
    await callback.message.edit_text(
        f"Часовой пояс: {user["timezone"]}\nСейчас у тебя {now} — верно?",
        reply_markup=timezone_kb(user["timezone"], back="set"),
    )
    await callback.answer()

@router.callback_query(TzCB.filter(F.index.is_not(None)))
async def tz_chosen(callback: CallbackQuery, callback_data: TzCB, db: Database, user):
    zone = TIMEZONES[callback_data.index][1]
    await db.set_timezone(user["user_id"], zone)
    now = datetime.now(ZoneInfo(zone)).strftime("%H:%M")
    await callback.message.edit_text(
        f"Часовой пояс: {zone}\nСейчас у тебя {now} — верно?",
        reply_markup=timezone_kb(zone, back="set"),
    )
    await callback.answer()


@router.callback_query(TzCB.filter(F.index.is_(None)))
async def tz_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Settings.waiting_timezone)
    await callback.message.edit_text(
        "Напиши название зоны, например <code>Europe/Rome</code>\n"
        "Список: en.wikipedia.org/wiki/List_of_tz_database_time_zones",
        reply_markup=cancel_kb("set"),
    )
    await callback.answer()


@router.message(Settings.waiting_timezone)
async def tz_entered(message: Message, state: FSMContext, db: Database, user):
    zone = (message.text or "").strip()
    try:
        now = datetime.now(ZoneInfo(zone)).strftime("%H:%M")
    except Exception:
        await message.answer("Не знаю такой зоны. Формат: Europe/Rome")
        return
    await db.set_timezone(user["user_id"], zone)
    await state.clear()
    await message.answer(f"Готово. Сейчас у тебя {now}")
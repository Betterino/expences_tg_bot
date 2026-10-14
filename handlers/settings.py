from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from callback import NavCB, TzCB
from constants import ADMIN_ID, TIMEZONES
from db import Database
from keyboards import cancel_kb, settings_kb, timezone_kb
from texts import Errors
from texts import Settings as SettingsTexts
from utils import clean_user_text
from validators import tz_index

from .screens import edit_text

router = Router(name="settings")

class Settings(StatesGroup):
    waiting_timezone = State()
    waiting_nickname = State()

@router.callback_query(NavCB.filter(F.to == "set"))
async def settings(callback: CallbackQuery, db: Database, state: FSMContext):
    await state.clear()
    is_admin = ADMIN_ID is not None and callback.from_user.id == ADMIN_ID
    await edit_text(callback.message, SettingsTexts.TITLE, reply_markup=settings_kb(is_admin))

@router.callback_query(NavCB.filter(F.to == "timez"))
async def timezones(callback: CallbackQuery, db: Database,user):
    now = datetime.now(ZoneInfo(user["timezone"])).strftime("%H:%M")
    await edit_text(
        callback.message,
        SettingsTexts.TZ_CONFIRM.format(zone=user["timezone"], now=now),
        reply_markup=timezone_kb(user["timezone"], back="set"),
    )

@router.callback_query(TzCB.filter(F.index.is_not(None)))
async def tz_chosen(callback: CallbackQuery, callback_data: TzCB, db: Database, user, callback_answer):
    index = tz_index(callback_data.index)
    if index is None:
        callback_answer.text = Errors.BAD_SELECTION
        return
    zone = TIMEZONES[index][1]
    await db.set_timezone(user["user_id"], zone)
    now = datetime.now(ZoneInfo(zone)).strftime("%H:%M")
    await edit_text(
        callback.message,
        SettingsTexts.TZ_CONFIRM.format(zone=zone, now=now),
        reply_markup=timezone_kb(zone, back="set"),
    )


@router.callback_query(TzCB.filter(F.index.is_(None)))
async def tz_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Settings.waiting_timezone)
    await edit_text(
        callback.message,
        SettingsTexts.TZ_MANUAL_PROMPT,
        reply_markup=cancel_kb("set"),
    )


@router.message(Settings.waiting_timezone)
async def tz_entered(message: Message, state: FSMContext, db: Database, user):
    zone = (message.text or "").strip()
    try:
        now = datetime.now(ZoneInfo(zone)).strftime("%H:%M")
    except Exception:
        await message.answer(SettingsTexts.TZ_UNKNOWN)
        return
    await db.set_timezone(user["user_id"], zone)
    await state.clear()
    await message.answer(SettingsTexts.TZ_SAVED.format(now=now))


@router.callback_query(NavCB.filter(F.to == "nickname"))
async def nickname_prompt(callback: CallbackQuery, state: FSMContext, user):
    await state.set_state(Settings.waiting_nickname)
    current = user["nickname"] or SettingsTexts.NO_NICKNAME
    await edit_text(
        callback.message,
        SettingsTexts.NICKNAME_PROMPT.format(current=current),
        reply_markup=cancel_kb("set"),
    )


@router.message(Settings.waiting_nickname)
async def nickname_entered(message: Message, state: FSMContext, db: Database, user):
    nickname = clean_user_text(message.text, 20)
    if nickname is None:
        await message.answer(SettingsTexts.NICKNAME_EMPTY)
        return
    await db.set_nickname(user["user_id"], nickname)
    await state.clear()
    await message.answer(SettingsTexts.NICKNAME_SAVED.format(nickname=nickname))

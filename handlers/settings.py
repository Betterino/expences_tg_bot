from datetime import datetime
from callback import  TzCB,NavCB
from keyboards import  cancel_kb,timezone_kb,settings_kb
import html

from aiogram import  F,Router

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from constants import TIMEZONES
from zoneinfo import ZoneInfo

from db import Database

from texts import Settings as SettingsTexts

from aiogram.types import Message, CallbackQuery




router = Router(name="settings")

class Settings(StatesGroup):
    waiting_timezone = State()
    waiting_nickname = State()

@router.callback_query(NavCB.filter(F.to == "set"))
async def settings(callback: CallbackQuery, db: Database, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(text=SettingsTexts.TITLE,reply_markup=settings_kb())
    pass

@router.callback_query(NavCB.filter(F.to == "timez"))
async def timezones(callback: CallbackQuery, db: Database,user):
    now = datetime.now(ZoneInfo(user["timezone"])).strftime("%H:%M")
    await callback.message.edit_text(
        SettingsTexts.TZ_CONFIRM.format(zone=user["timezone"], now=now),
        reply_markup=timezone_kb(user["timezone"], back="set"),
    )
    await callback.answer()

@router.callback_query(TzCB.filter(F.index.is_not(None)))
async def tz_chosen(callback: CallbackQuery, callback_data: TzCB, db: Database, user):
    zone = TIMEZONES[callback_data.index][1]
    await db.set_timezone(user["user_id"], zone)
    now = datetime.now(ZoneInfo(zone)).strftime("%H:%M")
    await callback.message.edit_text(
        SettingsTexts.TZ_CONFIRM.format(zone=zone, now=now),
        reply_markup=timezone_kb(zone, back="set"),
    )
    await callback.answer()


@router.callback_query(TzCB.filter(F.index.is_(None)))
async def tz_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Settings.waiting_timezone)
    await callback.message.edit_text(
        SettingsTexts.TZ_MANUAL_PROMPT,
        reply_markup=cancel_kb("set"),
    )
    await callback.answer()


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
    await callback.message.edit_text(
        SettingsTexts.NICKNAME_PROMPT.format(current=current),
        reply_markup=cancel_kb("set"),
    )
    await callback.answer()


@router.message(Settings.waiting_nickname)
async def nickname_entered(message: Message, state: FSMContext, db: Database, user):
    nickname = html.escape((message.text or "").strip())[:20]
    if not nickname:
        await message.answer(SettingsTexts.NICKNAME_EMPTY)
        return
    await db.set_nickname(user["user_id"], nickname)
    await state.clear()
    await message.answer(SettingsTexts.NICKNAME_SAVED.format(nickname=nickname))
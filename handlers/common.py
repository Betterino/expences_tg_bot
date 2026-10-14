from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.callback_answer import CallbackAnswer

from callback import CatPageCB, NavCB
from constants import CHANGELOG_URL, VERSION
from db import Database
from keyboards import onboarding_kb, to_menu
from texts import About, Errors, Onboarding, Screens
from validators import valid_kind, valid_mode
from views import about_view

from .screens import answer_rich, edit_rich, render_categories_screen, show_menu

router = Router(name="common")


### Отмена состояния
@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(Screens.CANCELLED)
    await show_menu(message, edit=False)

### Команда старта
@router.message(Command("start"))
async def handle_start(message: Message, budget_id):
    if budget_id is None:
        await message.answer(Onboarding.START_TEXT, reply_markup=onboarding_kb())
    else:
        await show_menu(message, edit=False)

### Команда помощи -- тот же экран, что и кнопка "Меню" (её collapsible-блок и есть справка)
@router.message(Command("help"))
async def handle_help(message: Message):
    await show_menu(message, edit=False)


@router.callback_query(NavCB.filter(F.to == "menu"))
async def main_menu_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_menu(callback.message, edit=True)


@router.message(Command("about"))
async def about_command(message: Message):
    blocks = about_view(VERSION, About.SUMMARY, CHANGELOG_URL)
    await answer_rich(message, blocks, reply_markup=to_menu())


@router.callback_query(NavCB.filter(F.to == "about"))
async def about_screen(callback: CallbackQuery):
    blocks = about_view(VERSION, About.SUMMARY, CHANGELOG_URL)
    await edit_rich(callback.message, blocks, reply_markup=to_menu())


### страницы категорий
@router.callback_query(CatPageCB.filter())
async def display_pages_cat(callback: CallbackQuery, db: Database, callback_data: CatPageCB, budget_id: int,
                            callback_answer: CallbackAnswer):
    # purpose has its own domain (expense|income|EDIT_PURPOSE values) and is only ever
    # echoed back onto buttons, but kind/mode end up in DB queries and FSM -- check them.
    if valid_kind(callback_data.kind) is None or valid_mode(callback_data.mode) is None:
        callback_answer.text = Errors.BAD_SELECTION
        return
    await render_categories_screen(
        callback, db, budget_id,
        purpose=callback_data.purpose, page=callback_data.page,
        kind=callback_data.kind, mode=callback_data.mode,
    )



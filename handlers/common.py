from callback import NavCB, CatPageCB
from keyboards import main_menu, onboarding_kb
from db import Database
from .screens import render_categories_screen
from aiogram import F,Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from texts import START_TEXT,MENU,CANCEL
router = Router(name="common")


### Отмена состояния
@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(CANCEL+MENU, reply_markup=main_menu())

### Команда старта
@router.message(Command("start"))
async def handle_start(message: Message, budget_id):
    if budget_id is None:
        await message.answer(START_TEXT, reply_markup=onboarding_kb())
        ### Добавить сюда текст с пояснениями и тд
    else:
        await message.answer(MENU,reply_markup=main_menu())


@router.callback_query(NavCB.filter(F.to == "menu"))
async def main_menu_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(text=MENU,reply_markup=main_menu())


### страницы категорий
@router.callback_query(CatPageCB.filter())
async def display_pages_cat(callback: CallbackQuery, db: Database, callback_data: CatPageCB, budget_id: int):
    await render_categories_screen(callback,db,budget_id,callback_data.purpose,callback_data.page,callback_data.kind)



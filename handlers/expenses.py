from datetime import datetime,timedelta
from callback import NavCB, CategoryCB, AddCB
from keyboards import  main_menu,  categories_kb,date_expense_kb,cancel_kb,added_confirm_kb
from db import Database
from utils import parse_amount, format_money,  calc_page, today, parse_date
from aiogram import  F,Router
from aiogram.types import Message, CallbackQuery
from .screens import render_categories_screen
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from zoneinfo import ZoneInfo
from constants import PER_PAGE
from texts import Screens, Prompts, Errors, Stats

router = Router(name="expenses")

class AddExpense(StatesGroup):
    waiting_amount = State()
    waiting_date = State()

### Добавление траты
@router.callback_query(NavCB.filter(F.to.in_({"expense", "income"})))
async def start_add(callback: CallbackQuery, state: FSMContext, db: Database,callback_data: NavCB, budget_id,user):
    if budget_id is None:
        await callback.message.answer(Errors.NO_BUDGET)
        return
    now = datetime.now(ZoneInfo(user["timezone"])).strftime("%d/%m %H:%M")
    await callback.message.edit_text(text=Prompts.CHOOSE_DATE_ADD.format(now=now),reply_markup=date_expense_kb(callback_data.to))


@router.callback_query(AddCB.filter())
async def start_add(callback: CallbackQuery, state: FSMContext, db: Database, callback_data: AddCB, budget_id):
    await state.update_data(kind=callback_data.kind)
    match callback_data.mode:
        case "today":
            await state.update_data(mode="today")
            await render_categories_screen(callback,db,budget_id,callback_data.kind,1,callback_data.kind)
            return
        case "yesterday":
            await state.update_data(mode="yesterday")
            await render_categories_screen(callback,db,budget_id,callback_data.kind,1,callback_data.kind)
        case "date":
            await state.update_data(mode="date")
            await state.set_state(AddExpense.waiting_date)
            await callback.message.edit_text(Prompts.INPUT_DATE_ADD,reply_markup=cancel_kb("menu"))



@router.message(AddExpense.waiting_date)
async def data_entered(message:Message,state:FSMContext,db: Database,budget_id,tz):
    my_date = parse_date(message.text,tz)
    if my_date is None:
        await message.answer(Errors.BAD_DATE)
        return
    await state.update_data(my_date=my_date)
    data = await state.get_data()
    kind = data["kind"]
    categories = await db.list_active_categories(budget_id,kind)
    max_page = len(categories)// PER_PAGE + (1 if len(categories) % PER_PAGE != 0 else 0)
    categories = calc_page(categories,1)
    text = Screens.CATEGORY_PICKER[kind]
    text += Screens.PAGE.format(page=1, max_page=max_page)
    if len(categories) == 0:
        text = Errors.BAD_PAGE
    await message.answer(text=text, reply_markup=categories_kb(categories,1,max_page,kind))

### Сообщение при вводе трат, после ввода значения
@router.message(AddExpense.waiting_amount)
async def amount_entered(message: Message, state: FSMContext, db: Database, budget_id,tz):
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer(Errors.BAD_AMOUNT)
        return                                   # состояние НЕ сбрасываем
    data = await state.get_data()
    my_date = today(tz)
    if data["mode"] == "yesterday":
        my_date -= timedelta(days=1)
    if data["mode"] == "date":
        my_date = data["my_date"]
    kind = data.get("kind", "expense")
    await db.add_expense(budget_id, message.from_user.id, data["category_id"],
                     amount, my_date.isoformat(), kind)
    mode, my_date_kept = data["mode"], data.get("my_date")
    await state.clear()
    ### сохраняем дату/режим, чтобы следующая трата на эту же дату не спрашивала дату заново
    await state.update_data(mode=mode, my_date=my_date_kept, kind=kind)
    await message.answer(Stats.ADDED.format(amount=format_money(amount)), reply_markup=added_confirm_kb(kind))

### Сообщение при вводе трат, после выбора категории
@router.callback_query(CategoryCB.filter(F.purpose.in_({"expense", "income"})))
async def category_chosen(callback: CallbackQuery, callback_data: CategoryCB, state: FSMContext):
    await state.update_data(category_id=callback_data.id, kind=callback_data.purpose)
    await state.set_state(AddExpense.waiting_amount)
    text = Prompts.AMOUNT[callback_data.purpose]
    await callback.message.edit_text(text)
    await callback.answer()

### "Добавить ещё на эту дату" -> сразу к выбору категории, минуя выбор даты
@router.callback_query(NavCB.filter(F.to == "add_again"))
async def add_again(callback: CallbackQuery, state: FSMContext, db: Database, callback_data: NavCB, budget_id):
    data = await state.get_data()
    if "mode" not in data:
        await callback.message.edit_text(text=Screens.MENU_TITLE,reply_markup=main_menu())
        return
    await render_categories_screen(callback,db,budget_id,callback_data.kind,1,callback_data.kind)


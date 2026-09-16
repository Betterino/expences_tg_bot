from keyboards import stats_kb,special_stats_kb,categories_kb,edit_kb
from db import Database
from utils import stats_bounds, create_stats_text, calc_page, parse_categories_edit
from aiogram.types import  CallbackQuery
from aiogram.fsm.context import FSMContext
from constants import PER_PAGE, PURPOSE_DICT_SCREENS

### Stat screen
async def render_special_stats_screen(year_start, month_start, year_end, month_end, db: Database, budget_id, callback: CallbackQuery):
    start, end = stats_bounds(year_start, month_start, year_end, month_end)
    total_e = await db.stats_total(budget_id, start, end,"expense")
    rows = await db.expense_by_category(budget_id, start, end)
    total_i = await db.stats_total(budget_id, start, end,"income")
    income = await db.income_by_category(budget_id,start,end)
    text = create_stats_text(start,end,total_e,rows,income,total_i)
    await callback.message.edit_text(text,reply_markup=special_stats_kb())

async def render_stats_screen(year,month,db: Database, budget_id, callback: CallbackQuery):
    start, end = stats_bounds(year, month, year, month)
    total_e = await db.stats_total(budget_id, start, end,"expense")
    rows = await db.expense_by_category(budget_id, start, end)
    total_i = await db.stats_total(budget_id, start, end,"income")
    income = await db.income_by_category(budget_id,start,end)
    text = create_stats_text(start,end,total_e,rows,income,total_i)
    await callback.message.edit_text(text,reply_markup=stats_kb(year,month))


async def render_categories_screen(callback: CallbackQuery, db:Database, budget_id: int, purpose: str, page: int, kind: str = "expense"):
    if purpose == "dearchive":
        categories = await db.list_archived_categories(budget_id)
    elif purpose == "delete":
        categories = await db.list_all_categories(budget_id,kind)
    else:
        categories = await db.list_active_categories(budget_id,kind)
    max_page = len(categories)// PER_PAGE + (1 if len(categories) % PER_PAGE != 0 else 0)
    categories = calc_page(categories,page)
    text = PURPOSE_DICT_SCREENS[purpose]
    text += f"Страница {page:2d}/{max_page:2d}"
    if len(categories) == 0:
        text = "Категорий для этого действия нет"
    await callback.message.edit_text(text=text, reply_markup=categories_kb(categories,page,max_page,purpose,kind))

async def build_edit_screen(db: Database, budget_id: int, text: str = "",kind: str = "expense",):
    categories = await db.all_categories(budget_id,kind)
    return text + parse_categories_edit(categories,kind)

async def render_edit_screen(callback: CallbackQuery,db: Database,budget_id: int,state: FSMContext,text: str, kind: str = "expense"):
    await state.clear()
    categories = await db.all_categories(budget_id,kind)
    text += parse_categories_edit(categories,kind)
    await callback.message.edit_text(text=text,reply_markup=edit_kb(kind))
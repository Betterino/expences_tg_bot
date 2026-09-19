from datetime import date
from callback import NavCB,RangeCB, MonthCB,StatsCB
from keyboards import choose_range_kb, months_kb,special_stats_kb
from db import Database
from utils import stats_bounds
from views import stats_view
from aiogram import F,Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import  CallbackQuery, Message
from .screens import render_stats_screen,render_special_stats_screen, load_stats, answer_rich
from texts import MONTHS, Errors, Screens, Stats
class StatsRange(StatesGroup):
    waiting_year = State()
    waiting_month = State()
    waiting_months = State()

router = Router(name="onboard")

### Вывод статистики
@router.callback_query(NavCB.filter(F.to == "stats"))
async def display_stats(callback: CallbackQuery, db: Database, budget_id):
    if budget_id is None:
        await callback.message.edit_text(Errors.NO_BUDGET)
        return
    current = date.today()
    await render_stats_screen(current.year,current.month,db,budget_id,callback)

@router.callback_query(StatsCB.filter())
async def display_page_stats(callback: CallbackQuery, callback_data: StatsCB, db: Database, budget_id, ):
    year = callback_data.year
    month = callback_data.month
    await render_stats_screen(year,month,db,budget_id,callback)

@router.callback_query(NavCB.filter(F.to == "stats_choose"))
async def render_choose(callback:CallbackQuery):
    await callback.message.edit_text(Screens.CHOOSE_RANGE,reply_markup=choose_range_kb())

@router.callback_query(RangeCB.filter())
async def choose_ranges(callback: CallbackQuery, callback_data: RangeCB,state: FSMContext):
    match callback_data.year_month:
        case "year":
            await state.set_state(StatsRange.waiting_year)
            await callback.message.edit_text(Stats.CHOOSE_YEAR)
        case "month":
            await callback.message.edit_text(Stats.CHOOSE_MONTH,reply_markup=months_kb("single"))
        case "months":
            await callback.message.edit_text(Stats.CHOOSE_START_MONTH,reply_markup=months_kb("from"))

@router.message(StatsRange.waiting_year)
async def input_year(message: Message,state:FSMContext, db: Database,budget_id):
    try:
        year = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer(Errors.BAD_YEAR)
        return
    await state.clear()
    start, end = stats_bounds(year,1,year,12)
    data = await load_stats(db, budget_id, start, end)
    await answer_rich(message, stats_view(data), reply_markup=special_stats_kb())

@router.callback_query(MonthCB.filter())
async def input_month(callback: CallbackQuery,callback_data: MonthCB,state:FSMContext, db: Database,budget_id):
    match callback_data.purpose:
        case "single":
            month = callback_data.month + 1 
            current = date.today()
            await render_stats_screen(current.year,month,db,budget_id,callback)
        case "from":
            month = callback_data.month
            await state.update_data(from_month=month)
            await callback.message.edit_text(Stats.GOT_MONTH.format(month=MONTHS[month]),reply_markup=months_kb("to",start=month))
        case "to":
            data = await state.get_data()
            start = data["from_month"] + 1
            end = callback_data.month + 1
            current = date.today()
            await render_special_stats_screen(current.year,start,current.year,end,db,budget_id,callback)



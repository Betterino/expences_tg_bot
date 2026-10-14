from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from callback import MonthCB, NavCB, RangeCB, StatsCB
from db import Database
from keyboards import choose_range_kb, months_kb, special_stats_kb
from texts import MONTHS, Errors, Screens, Stats
from utils import stats_bounds, today
from validators import clamp_month_index, clamp_stats_month, clamp_year
from views import stats_view

from .screens import answer_rich, edit_text, load_stats, render_special_stats_screen, render_stats_screen


class StatsRange(StatesGroup):
    waiting_year = State()
    waiting_month = State()
    waiting_months = State()

router = Router(name="stats")

### Вывод статистики
@router.callback_query(NavCB.filter(F.to == "stats"))
async def display_stats(callback: CallbackQuery, db: Database, budget_id, tz):
    if budget_id is None:
        await edit_text(callback.message, Errors.NO_BUDGET)
        return
    current = today(tz)
    await render_stats_screen(current.year,current.month,db,budget_id,callback)

@router.callback_query(StatsCB.filter())
async def display_page_stats(
    callback: CallbackQuery, callback_data: StatsCB, db: Database, budget_id, callback_answer
):
    year = clamp_year(callback_data.year)
    month = clamp_stats_month(callback_data.month)
    if year is None or month is None:
        callback_answer.text = Errors.BAD_SELECTION
        return
    await render_stats_screen(year,month,db,budget_id,callback)

@router.callback_query(NavCB.filter(F.to == "stats_choose"))
async def render_choose(callback:CallbackQuery):
    await edit_text(callback.message, Screens.CHOOSE_RANGE, reply_markup=choose_range_kb())

@router.callback_query(RangeCB.filter())
async def choose_ranges(callback: CallbackQuery, callback_data: RangeCB,state: FSMContext):
    match callback_data.year_month:
        case "year":
            await state.set_state(StatsRange.waiting_year)
            await edit_text(callback.message, Stats.CHOOSE_YEAR)
        case "month":
            await edit_text(callback.message, Stats.CHOOSE_MONTH, reply_markup=months_kb("single"))
        case "months":
            await edit_text(callback.message, Stats.CHOOSE_START_MONTH, reply_markup=months_kb("from"))

@router.message(StatsRange.waiting_year)
async def input_year(message: Message,state:FSMContext, db: Database,budget_id):
    try:
        year = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer(Errors.BAD_YEAR)
        return
    if clamp_year(year) is None:
        await message.answer(Errors.BAD_YEAR)
        return
    await state.clear()
    start, end = stats_bounds(year,1,year,12)
    data = await load_stats(db, budget_id, start, end)
    await answer_rich(message, stats_view(data), reply_markup=special_stats_kb())

@router.callback_query(MonthCB.filter())
async def input_month(
    callback: CallbackQuery,
    callback_data: MonthCB,
    state: FSMContext,
    db: Database,
    budget_id,
    tz,
    callback_answer,
):
    if clamp_month_index(callback_data.month) is None:
        callback_answer.text = Errors.BAD_SELECTION
        return
    match callback_data.purpose:
        case "single":
            month = callback_data.month + 1
            current = today(tz)
            await render_stats_screen(current.year,month,db,budget_id,callback)
        case "from":
            month = callback_data.month
            await state.update_data(from_month=month)
            await edit_text(
                callback.message,
                Stats.GOT_MONTH.format(month=MONTHS[month]),
                reply_markup=months_kb("to", start=month),
            )
        case "to":
            data = await state.get_data()
            # "from" is stored in FSM data, not FSM *state* -- any state.clear() on the
            # way here (every menu nav) drops it silently, so a stale "to" tap must
            # re-prompt instead of KeyError-ing (BUG-3).
            from_month = data.get("from_month")
            if from_month is None:
                await edit_text(callback.message, Stats.CHOOSE_START_MONTH, reply_markup=months_kb("from"))
                return
            start = from_month + 1
            end = callback_data.month + 1
            current = today(tz)
            await render_special_stats_screen(current.year,start,current.year,end,db,budget_id,callback)



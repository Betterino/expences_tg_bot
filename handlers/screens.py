from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import richtext
from db import Database
from keyboards import categories_kb, edit_kb, special_stats_kb, stats_kb
from utils import calc_page, stats_bounds
from views import TableData, categories_view, stats_view
from constants import PER_PAGE
from texts import Screens, Errors


async def edit_rich(message: Message, blocks: list[richtext.Block], reply_markup=None) -> None:
    """Swallow only "message is not modified" -- Telegram rejects an editMessageText
    whose text AND markup are byte-identical to what is already on screen, which is
    exactly what re-tapping the currently selected month/page produces. Unhandled it
    reaches @dp.error() and shows "Что-то сломалось" for a no-op."""
    try:
        await message.edit_text(rich_message=richtext.message(blocks), reply_markup=reply_markup)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise


async def answer_rich(message: Message, blocks: list[richtext.Block], reply_markup=None) -> None:
    await message.answer_rich(rich_message=richtext.message(blocks), reply_markup=reply_markup)


### Stat screen
async def load_stats(db: Database, budget_id: int, start: str, end: str) -> TableData:
    return TableData(
        start=start,
        end=end,
        total_e=await db.stats_total(budget_id, start, end, "expense"),
        expense=await db.expense_by_category(budget_id, start, end),
        income=await db.income_by_category(budget_id, start, end),
        total_i=await db.stats_total(budget_id, start, end, "income"),
    )


async def render_special_stats_screen(year_start, month_start, year_end, month_end, db: Database, budget_id, callback: CallbackQuery):
    start, end = stats_bounds(year_start, month_start, year_end, month_end)
    data = await load_stats(db, budget_id, start, end)
    await edit_rich(callback.message, stats_view(data), reply_markup=special_stats_kb())

async def render_stats_screen(year,month,db: Database, budget_id, callback: CallbackQuery):
    start, end = stats_bounds(year, month, year, month)
    data = await load_stats(db, budget_id, start, end)
    await edit_rich(callback.message, stats_view(data), reply_markup=stats_kb(year, month))


async def render_categories_screen(callback: CallbackQuery, db:Database, budget_id: int, purpose: str, page: int, kind: str = "expense"):
    if purpose == "dearchive":
        categories = await db.list_archived_categories(budget_id,kind)
    elif purpose == "delete":
        categories = await db.list_all_categories(budget_id,kind)
    else:
        categories = await db.list_active_categories(budget_id,kind)
    max_page = len(categories)// PER_PAGE + (1 if len(categories) % PER_PAGE != 0 else 0)
    categories = calc_page(categories,page)
    text = Screens.CATEGORY_PICKER[purpose]
    text += Screens.PAGE.format(page=page, max_page=max_page)
    if len(categories) == 0:
        text = Errors.BAD_PAGE
    await callback.message.edit_text(text=text, reply_markup=categories_kb(categories,page,max_page,purpose,kind))

async def build_edit_screen(db: Database, budget_id: int, prefix: str = "", kind: str = "expense") -> list[richtext.Block]:
    categories = await db.all_categories(budget_id,kind)
    return categories_view(categories, kind, prefix)

async def render_edit_screen(callback: CallbackQuery,db: Database,budget_id: int,state: FSMContext,prefix: str, kind: str = "expense"):
    await state.clear()
    blocks = await build_edit_screen(db, budget_id, prefix, kind)
    await edit_rich(callback.message, blocks, reply_markup=edit_kb(kind))

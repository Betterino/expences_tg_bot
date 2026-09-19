from aiogram import F, Router
from aiogram.types import CallbackQuery

from callback import HistoryPageCB, NavCB
from constants import PER_PAGE
from db import Database
from keyboards import history_kb
from views import history_view
from texts import Errors
from .screens import edit_rich

router = Router(name="history")


async def render_history_screen(callback: CallbackQuery, db: Database, budget_id: int, page: int, kind: str | None = None):
    total = await db.count_transactions(budget_id, kind)
    max_page = max(total // PER_PAGE + (1 if total % PER_PAGE != 0 else 0), 1)
    page = min(max(page, 1), max_page)
    rows = await db.list_recent_transactions(budget_id, PER_PAGE, PER_PAGE * (page - 1), kind)
    blocks = history_view(rows, page, max_page)
    await edit_rich(callback.message, blocks, reply_markup=history_kb(page, max_page, kind))


@router.callback_query(NavCB.filter(F.to == "history"))
async def open_history(callback: CallbackQuery, db: Database, budget_id):
    if budget_id is None:
        await callback.message.answer(Errors.NO_BUDGET)
        return
    await render_history_screen(callback, db, budget_id, 1)


@router.callback_query(HistoryPageCB.filter())
async def history_page(callback: CallbackQuery, callback_data: HistoryPageCB, db: Database, budget_id):
    await render_history_screen(callback, db, budget_id, callback_data.page, callback_data.kind)

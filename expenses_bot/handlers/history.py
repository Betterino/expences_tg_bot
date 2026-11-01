from aiogram import F, Router
from aiogram.types import CallbackQuery

from expenses_bot.constants import PER_PAGE
from expenses_bot.db import Database
from expenses_bot.ui.callback import HistoryPageCB, NavCB
from expenses_bot.ui.keyboards import history_kb
from expenses_bot.ui.texts import Errors
from expenses_bot.ui.views import history_view
from expenses_bot.utils import page_count
from expenses_bot.validators import normalize_history

from .screens import edit_rich

router = Router(name="history")


async def render_history_screen(
    callback: CallbackQuery,
    db: Database,
    budget_id: int,
    page: int,
    kind: str | None = None,
    who: str = "all",
    sort: str = "id",
):
    # added_by comes from callback.from_user.id, not the middleware `user` row -- keeps
    # the fakes simple and matches how handlers/expenses.py:81 identifies the actor.
    kind, who, sort = normalize_history(kind, who, sort)
    added_by = callback.from_user.id if who == "mine" else None
    total = await db.count_transactions(budget_id, kind, added_by)
    max_page = max(page_count(total), 1)
    page = min(max(page, 1), max_page)
    rows = await db.list_recent_transactions(budget_id, PER_PAGE, PER_PAGE * (page - 1), kind, added_by, sort)
    blocks = history_view(rows, page, max_page, kind, who, sort)
    await edit_rich(callback.message, blocks, reply_markup=history_kb(page, max_page, kind, who, sort))


@router.callback_query(NavCB.filter(F.to == "history"))
async def open_history(callback: CallbackQuery, db: Database, budget_id):
    if budget_id is None:
        await callback.message.answer(Errors.NO_BUDGET)
        return
    await render_history_screen(callback, db, budget_id, 1)


@router.callback_query(HistoryPageCB.filter())
async def history_page(callback: CallbackQuery, callback_data: HistoryPageCB, db: Database, budget_id):
    await render_history_screen(
        callback, db, budget_id, callback_data.page, callback_data.kind, callback_data.who, callback_data.sort
    )

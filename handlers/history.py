from aiogram import F, Router
from aiogram.types import CallbackQuery

from callback import HistoryPageCB, NavCB
from constants import PER_PAGE
from db import Database
from keyboards import history_kb
from utils import format_money, format_tx_date
from texts import History, Errors

router = Router(name="history")


async def render_history_screen(callback: CallbackQuery, db: Database, budget_id: int, page: int, kind: str | None = None):
    total = await db.count_transactions(budget_id, kind)
    max_page = max(total // PER_PAGE + (1 if total % PER_PAGE != 0 else 0), 1)
    page = min(max(page, 1), max_page)
    rows = await db.list_recent_transactions(budget_id, PER_PAGE, PER_PAGE * (page - 1), kind)
    if not rows:
        text = History.EMPTY
    else:
        lines = [History.HEADER.format(page=page, max_page=max_page)]
        for r in rows:
            sign = "+" if r["kind"] == "income" else "-"
            who = r["nickname"] or f"ID {r['added_by']}"
            lines.append(
                f"{format_tx_date(r['date'])} {sign}{format_money(r['amount'])} | {r['category_name']} | {who}"
            )
        text = "\n".join(lines)
    await callback.message.edit_text(text=text, reply_markup=history_kb(page, max_page, kind))


@router.callback_query(NavCB.filter(F.to == "history"))
async def open_history(callback: CallbackQuery, db: Database, budget_id):
    if budget_id is None:
        await callback.message.answer(Errors.NO_BUDGET)
        return
    await render_history_screen(callback, db, budget_id, 1)


@router.callback_query(HistoryPageCB.filter())
async def history_page(callback: CallbackQuery, callback_data: HistoryPageCB, db: Database, budget_id):
    await render_history_screen(callback, db, budget_id, callback_data.page, callback_data.kind)

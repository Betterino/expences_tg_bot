"""Import of many transactions at once from a JSON file (importer.py does the parsing).

Flow: "📥 Импорт" -> schema.json + AI prompt -> the user sends a .json document ->
preview -> "✅ Записать" -> done, with "↩️ Отменить импорт" on the result.

The parsed rows can't ride on the "Записать" button (64 bytes of callback data), so they
wait in FSM data and are read back through require_flow: a "Меню" tap in between means
"Действие устарело", not a KeyError. The undo button *can* carry its import_id, so it
does -- no FSM at all, and it keeps working after any number of state.clear()s.
"""
import json
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.utils.callback_answer import CallbackAnswer

from expenses_bot import importer
from expenses_bot.constants import KINDS
from expenses_bot.db import Database
from expenses_bot.ui.callback import ImportCB, NavCB
from expenses_bot.ui.keyboards import import_done_kb, import_preview_kb, import_undo_confirm_kb, to_menu
from expenses_bot.ui.texts import Errors, Import
from expenses_bot.utils import fit, format_money, format_tx_date, today, visible

from .flow import require_flow
from .screens import edit_text

logger = logging.getLogger(__name__)

router = Router(name="import")


class ImportFlow(StatesGroup):
    confirm = State()


async def _categories(db: Database, budget_id: int) -> dict[str, dict[str, int]]:
    """kind -> {stored name -> category_id}, active categories only (the same set the
    add-expense picker offers, so an archived category can't be revived by a file)."""
    return {
        kind: {row["name"]: row["category_id"] for row in await db.list_active_categories(budget_id, kind)}
        for kind in KINDS
    }


@router.callback_query(NavCB.filter(F.to == "import"))
async def import_intro(callback: CallbackQuery, state: FSMContext, db: Database, budget_id, tz):
    await state.clear()
    if budget_id is None:
        await callback.message.answer(Errors.NO_BUDGET)
        return
    now = today(tz)
    categories = await _categories(db, budget_id)
    names = {kind: [visible(n) for n in by_name] for kind, by_name in categories.items()}
    schema = importer.build_schema(names, now)
    schema["examples"] = [importer.example(names, now)]
    payload = json.dumps(schema, ensure_ascii=False, indent=2).encode()
    await edit_text(callback.message, Import.INTRO.format(max_rows=importer.MAX_ROWS))
    # answer_document uploads bytes we hold in memory: BufferedInputFile wraps them with a
    # filename, no temp file on disk needed.
    await callback.message.answer_document(
        BufferedInputFile(payload, filename="schema.json"), caption=Import.SCHEMA_CAPTION
    )
    await callback.message.answer(
        Import.PROMPT.format(prompt=fit(importer.ai_prompt(now), 3000)), reply_markup=to_menu()
    )


# F.document on a router mounted *before* expenses.router: otherwise a file sent while the
# bot waits for an amount would be swallowed by amount_entered (it filters on state only).
@router.message(F.document)
async def import_file(message: Message, state: FSMContext, bot: Bot, db: Database, budget_id, tz):
    await state.clear()
    if budget_id is None:
        await message.answer(Errors.NO_BUDGET)
        return
    document = message.document
    if not (document.file_name or "").lower().endswith(".json"):
        await message.answer(Import.NOT_JSON_FILE)
        return
    # Check the size Telegram reports *before* downloading: no point pulling a 20 MB file
    # into memory just to reject it.
    if (document.file_size or 0) > importer.MAX_FILE_BYTES:
        await message.answer(Import.TOO_BIG.format(kb=importer.MAX_FILE_BYTES // 1024))
        return
    # bot.download() with no destination returns an in-memory BytesIO. It's real network
    # I/O (getFile + HTTP fetch), awaited, so other users' updates keep flowing meanwhile.
    buffer = await bot.download(document)
    raw = buffer.read(importer.MAX_FILE_BYTES + 1)
    if len(raw) > importer.MAX_FILE_BYTES:
        await message.answer(Import.TOO_BIG.format(kb=importer.MAX_FILE_BYTES // 1024))
        return

    result = importer.parse_import(raw, await _categories(db, budget_id), today(tz))
    if result.errors:
        shown = result.errors[: importer.MAX_ERRORS_SHOWN]
        # errors echo file content (category names...) -- fit() escapes it for parse_mode=HTML
        lines = [f"• {fit(e, 200)}" for e in shown]
        if len(result.errors) > len(shown):
            lines.append(Import.MORE_ERRORS.format(n=len(result.errors) - len(shown)))
        await message.answer(Import.ERRORS.format(errors="\n".join(lines)))
        return

    digest = importer.digest(result.rows)
    existing = await db.find_import(budget_id, digest)
    if existing is not None:
        await message.answer(
            Import.DUPLICATE.format(when=existing["created_at"][:10], count=existing["row_count"]),
            reply_markup=to_menu(),
        )
        return

    s = importer.summary(result.rows)
    await state.set_state(ImportFlow.confirm)
    await state.update_data(import_rows=[[r.date, r.kind, r.category_id, r.amount] for r in result.rows])
    await message.answer(
        Import.PREVIEW.format(
            count=s["count"], first=format_tx_date(s["first"]), last=format_tx_date(s["last"]),
            e_count=s["counts"]["expense"], e_total=format_money(s["totals"]["expense"], sep=" "),
            i_count=s["counts"]["income"], i_total=format_money(s["totals"]["income"], sep=" "),
        ),
        reply_markup=import_preview_kb(),
    )


@router.callback_query(ImportCB.filter(F.action == "commit"))
async def import_commit(callback: CallbackQuery, state: FSMContext, db: Database, budget_id,
                        callback_answer: CallbackAnswer):
    data = await require_flow(state, callback, "import_rows", callback_answer=callback_answer)
    if data is None:
        return
    await state.clear()
    rows = [importer.ImportRow(*row) for row in data["import_rows"]]
    # Categories are re-checked here, not trusted from the preview: one could have been
    # archived/deleted (or the user moved to another budget) between preview and tap.
    active = await _categories(db, budget_id)
    valid_ids = {cid for by_name in active.values() for cid in by_name.values()}
    if any(r.category_id not in valid_ids for r in rows):
        callback_answer.text = Errors.FLOW_EXPIRED
        await edit_text(callback.message, Errors.FLOW_EXPIRED, reply_markup=to_menu())
        return
    import_id = await db.create_import(budget_id, callback.from_user.id, importer.digest(rows), rows)
    if import_id is None:  # a second "Записать" tap, or the same file committed meanwhile
        await edit_text(callback.message, Import.ALREADY_COMMITTED, reply_markup=to_menu())
        return
    logger.info("импорт %s: %s записей, budget=%s", import_id, len(rows), budget_id)
    await edit_text(callback.message, Import.DONE.format(count=len(rows)),
                    reply_markup=import_done_kb(import_id))


@router.callback_query(ImportCB.filter(F.action == "undo_ask"))
async def import_undo_ask(callback: CallbackQuery, callback_data: ImportCB, db: Database, budget_id,
                          callback_answer: CallbackAnswer):
    found = await db.get_import(budget_id, callback_data.id)
    if found is None:
        callback_answer.text = Import.UNDO_GONE
        return
    await edit_text(callback.message, Import.UNDO_CONFIRM.format(count=found["row_count"]),
                    reply_markup=import_undo_confirm_kb(callback_data.id))


@router.callback_query(ImportCB.filter(F.action == "undo"))
async def import_undo(callback: CallbackQuery, callback_data: ImportCB, db: Database, budget_id,
                      callback_answer: CallbackAnswer):
    found = await db.get_import(budget_id, callback_data.id)
    if found is None or not await db.delete_import(budget_id, callback_data.id):
        callback_answer.text = Import.UNDO_GONE
        await edit_text(callback.message, Import.UNDO_GONE, reply_markup=to_menu())
        return
    logger.info("импорт %s отменён, budget=%s", callback_data.id, budget_id)
    await edit_text(callback.message, Import.UNDONE.format(count=found["row_count"]), reply_markup=to_menu())

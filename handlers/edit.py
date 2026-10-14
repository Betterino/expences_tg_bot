from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import richtext
from callback import CategoryCB, NavCB
from constants import EDIT_PURPOSE
from db import Database
from keyboards import cancel_kb, confirm, edit_archived_kb, edit_kb
from texts import Categories, Errors
from utils import clean_user_text, parse_amount

from .flow import require_flow
from .screens import (
    answer_rich,
    build_edit_screen,
    edit_rich,
    edit_text,
    render_categories_screen,
    render_edit_screen,
)

router = Router(name="edit")

class CategoryName(StatesGroup):
    waiting_name = State()

class CategoryMax(StatesGroup):
    waiting_max = State()

class CategoryMaxCreate(StatesGroup):
    waiting_max_create = State()

@router.callback_query(NavCB.filter(F.to == "edit"))
async def choose_edit_categories(
    callback: CallbackQuery, state: FSMContext, callback_data: NavCB, db: Database, budget_id
):
    if budget_id is None:
        await callback.message.answer(Errors.NO_BUDGET)
        return
    await render_edit_screen(callback,db,budget_id,state,"",callback_data.kind)

@router.callback_query(NavCB.filter(F.to == "edit_cancel"))
async def cancel_edit_categories(
    callback: CallbackQuery, state: FSMContext, callback_data: NavCB, db: Database, budget_id
):
    await state.clear()
    await render_edit_screen(callback,db,budget_id,state,"",callback_data.kind)

@router.callback_query(NavCB.filter(F.to == "create_confirm"))
async def edit_categories_create(
    callback: CallbackQuery, state: FSMContext, callback_data: NavCB, db: Database, budget_id, callback_answer
):
    data = await require_flow(state, callback, "category_name", "sort_order", callback_answer=callback_answer)
    if data is None:
        return
    await db.add_category(data["category_name"],budget_id, 0,data["sort_order"],callback_data.kind)
    blocks = await build_edit_screen(
        db, budget_id, Categories.ADDED.format(name=data["category_name"]), callback_data.kind
    )
    await edit_rich(callback.message, blocks, reply_markup=confirm("edit_cat","edit",callback_data.kind))


@router.callback_query(CategoryCB.filter(F.purpose == "rename_confirm"))
async def edit_categories_rename(callback: CallbackQuery, state: FSMContext, callback_data: CategoryCB,
                                 db: Database, budget_id, callback_answer):
    # The id rides on the "Да" button (keyboards.confirm); only the typed name needs FSM.
    data = await require_flow(state, callback, "category_name", callback_answer=callback_answer)
    if data is None:
        return
    # callback_data.id is attacker-controlled -- rowcount==0 means it isn't
    # (or is no longer) a category in this budget (SEC-1).
    rowcount = await db.rename_category(budget_id, callback_data.id, data["category_name"])
    if rowcount == 0:
        callback_answer.text = Errors.NOT_FOUND
        await render_edit_screen(callback,db,budget_id,state,"",callback_data.kind)
        return
    renamed = Categories.RENAMED.format(name=data["category_name"])
    await render_edit_screen(callback, db, budget_id, state, renamed, callback_data.kind)

@router.callback_query(CategoryCB.filter(F.purpose == "confirm_delete"))
async def edit_categories_delete(callback: CallbackQuery, state: FSMContext, callback_data: CategoryCB,
                                 db: Database, budget_id, callback_answer):
    # Nothing read from FSM: the id comes from the "Да" button, scoped by budget_id in db.py (SEC-1).
    rowcount = await db.delete_category(budget_id, callback_data.id)
    if rowcount == 0:
        callback_answer.text = Errors.NOT_FOUND
        await render_edit_screen(callback,db,budget_id,state,"",callback_data.kind)
        return
    await render_edit_screen(callback,db,budget_id,state,Categories.DELETED,callback_data.kind)



@router.callback_query(NavCB.filter(F.to == "edit_cat"))
async def edit_categories_cat(
    callback: CallbackQuery, state: FSMContext, db: Database, callback_data: NavCB, budget_id
):
    blocks = await build_edit_screen(db, budget_id, "",callback_data.kind)
    blocks = blocks + [richtext.para(Categories.ASK_NEW_NAME)]
    await edit_rich(callback.message, blocks, reply_markup=cancel_kb("edit_cancel",callback_data.kind))
    await state.set_state(CategoryName.waiting_name)
    await state.update_data(mode="create", kind=callback_data.kind)

@router.callback_query(NavCB.filter(F.to.in_(EDIT_PURPOSE)))
async def open_category_picker(callback, callback_data: NavCB, db, budget_id):
    await render_categories_screen(
        callback, db, budget_id, purpose=EDIT_PURPOSE[callback_data.to], page=1, kind=callback_data.kind
    )

@router.callback_query(NavCB.filter(F.to == "edit_arch"))
async def edit_categories_arch(callback: CallbackQuery, callback_data: NavCB):
    await edit_text(
        callback.message, Categories.CHOOSE_ARCHIVE, reply_markup=edit_archived_kb(callback_data.kind)
    )

@router.callback_query(NavCB.filter(F.to == "create_max"))
async def edit_categories_max(callback: CallbackQuery,state: FSMContext,callback_data: NavCB):
    await state.set_state(CategoryMaxCreate.waiting_max_create)
    await state.update_data(kind=callback_data.kind)
    await edit_text(
        callback.message, Categories.ASK_MAX, reply_markup=cancel_kb("edit_cancel", callback_data.kind)
    )



@router.callback_query(CategoryCB.filter(F.purpose.in_({"archive", "dearchive"})))
async def archive_category(
    callback: CallbackQuery,
    db: Database,
    state: FSMContext,
    callback_data: CategoryCB,
    budget_id,
    callback_answer,
):
    # callback_data.id is attacker-controlled (SEC-1) -- both mutations are scoped by
    # budget_id in db.py and report back via rowcount whether a row was actually touched.
    if callback_data.purpose == "archive":
        rowcount = await db.archive_category(budget_id, callback_data.id)
    else:
        rowcount = await db.dearchive_category(budget_id, callback_data.id)
    await state.clear()
    if rowcount == 0:
        callback_answer.text = Errors.NOT_FOUND
    blocks = await build_edit_screen(db, budget_id, Categories.DONE if rowcount else "", callback_data.kind)
    await edit_rich(callback.message, blocks, reply_markup=edit_kb(callback_data.kind))

@router.callback_query(CategoryCB.filter(F.purpose == "changename"))
async def rename_category(callback: CallbackQuery, state: FSMContext,callback_data: CategoryCB):
    await state.set_state(CategoryName.waiting_name)
    await state.update_data(mode="rename",category_id=callback_data.id,kind=callback_data.kind)
    await edit_text(
        callback.message, Categories.ASK_NEW_NAME, reply_markup=cancel_kb("edit_cancel", callback_data.kind)
    )

@router.callback_query(CategoryCB.filter(F.purpose == "changemax"))
async def changemax_category(callback: CallbackQuery, state: FSMContext,callback_data: CategoryCB):
    await state.set_state(CategoryMax.waiting_max)
    await state.update_data(mode="",category_id=callback_data.id,kind=callback_data.kind)
    await edit_text(
        callback.message, Categories.ASK_MAX, reply_markup=cancel_kb("edit_cancel", callback_data.kind)
    )


@router.callback_query(CategoryCB.filter(F.purpose == "delete"))
async def delete_category(callback: CallbackQuery,callback_data:CategoryCB):
    markup = confirm("confirm_delete", "edit", callback_data.kind, category_id=callback_data.id)
    await edit_text(callback.message, Categories.DELETE_CONFIRM, reply_markup=markup)


@router.message(CategoryMaxCreate.waiting_max_create)
async def input_max_create(message: Message,state: FSMContext,db: Database,budget_id):
    if message.text is None:
        await message.answer(Errors.BAD_AMOUNT)
        return
    maximum = parse_amount(message.text)
    if maximum is None:
        await message.answer(Errors.BAD_AMOUNT)
        return
    data = await require_flow(state, message, "category_name", "sort_order", "kind")
    if data is None:
        return
    await db.add_category(data["category_name"],budget_id,maximum,data["sort_order"],data["kind"])
    blocks = await build_edit_screen(
        db, budget_id, Categories.ADDED.format(name=data["category_name"]), data["kind"]
    )
    await answer_rich(message, blocks, reply_markup=confirm("edit_cat","edit",data["kind"]))

@router.message(CategoryMax.waiting_max)
async def input_category_max(message: Message,state: FSMContext, db: Database, budget_id):
    if message.text is None:
        await message.answer(Errors.BAD_AMOUNT)
        return
    maximum = parse_amount(message.text)
    if maximum is None:
        await message.answer(Errors.BAD_AMOUNT)
        return
    data = await require_flow(state, message, "category_id", "kind")
    if data is None:
        return
    category_id = data["category_id"]
    rowcount = await db.change_maximum(budget_id, category_id, maximum)
    if rowcount == 0:
        await message.answer(Errors.NOT_FOUND)
        return
    blocks = await build_edit_screen(db, budget_id, Categories.MAX_CHANGED,data["kind"])
    await answer_rich(message, blocks, reply_markup=edit_kb(data["kind"]))

@router.message(CategoryName.waiting_name)
async def input_category_name(message: Message,state: FSMContext, db: Database, budget_id):
    category_name = clean_user_text(message.text, 15)
    if category_name is None:
        await message.answer(Categories.EMPTY_NAME)
        return
    data = await require_flow(state, message, "mode", "kind")
    if data is None:
        return
    mode = data["mode"]
    kind = data["kind"]
    if mode != "create" and await require_flow(state, message, "category_id") is None:
        return
    confirm_text = "rename_confirm"
    # rename's "Да" carries the id on the button; create has no id yet (None -> NavCB)
    confirm_id = None if mode == "create" else data["category_id"]
    if mode == "create":
        confirm_text = "create_confirm"
        sort_order = await db.get_maximum_sort_order(budget_id,kind) + 10
        await state.update_data(sort_order=sort_order)

    if await db.check_category_name(budget_id,category_name,kind) is not None:
        await state.update_data(category_name=category_name)
        markup = confirm(confirm_text, "edit_cancel", kind, category_id=confirm_id)
        await message.answer(Categories.NAME_EXISTS, reply_markup=markup)

    elif await db.check_category_name_archived(budget_id,category_name,kind) is not None:
        await state.update_data(category_name=category_name)
        markup = confirm(confirm_text, "edit_cancel", kind, category_id=confirm_id)
        await message.answer(Categories.NAME_EXISTS, reply_markup=markup)

    else:
        if mode == "create":
            await state.update_data(category_name=category_name)
            if kind == "expense":
                await message.answer(
                    text=Categories.PROMPT_MAXIMUM, reply_markup=confirm("create_max", "create_confirm", kind)
                )
            else:
                await db.add_category(category_name, budget_id, 0, sort_order, kind)
                blocks = await build_edit_screen(db, budget_id, Categories.ADDED.format(name=category_name),
                                               kind)
                await answer_rich(message, blocks, reply_markup=confirm("edit_cat", "edit", kind))

        else:
            rowcount = await db.rename_category(budget_id, data["category_id"], category_name)
            await state.clear()
            if rowcount == 0:
                await message.answer(Errors.NOT_FOUND)
                return
            renamed = Categories.RENAMED.format(name=category_name)
            blocks = await build_edit_screen(db, budget_id, renamed, kind)
            await answer_rich(message, blocks, reply_markup=edit_kb(kind))

from callback import NavCB,CategoryCB
from keyboards import confirm,edit_archived_kb,cancel_kb, edit_kb
from db import Database
from utils import parse_amount
from aiogram import  F,Router
from aiogram.types import  CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import html
from constants import EDIT_PURPOSE
from .screens import render_categories_screen,render_edit_screen,build_edit_screen
from texts import Categories, Errors
import logging

logger = logging.getLogger(__name__)

router = Router(name="edit")

class CategoryName(StatesGroup):
    waiting_name = State()

class CategoryMax(StatesGroup):
    waiting_max = State()

class CategoryMaxCreate(StatesGroup):
    waiting_max_create = State()

@router.callback_query(NavCB.filter(F.to == "edit"))
async def choose_edit_categories(callback: CallbackQuery, state: FSMContext, callback_data: NavCB, db: Database, budget_id):
    await render_edit_screen(callback,db,budget_id,state,"",callback_data.kind)

@router.callback_query(NavCB.filter(F.to == "edit_cancel"))
async def choose_edit_categories(callback: CallbackQuery, state: FSMContext, callback_data: NavCB, db: Database, budget_id):
    await state.clear()
    await render_edit_screen(callback,db,budget_id,state,"",callback_data.kind)

@router.callback_query(NavCB.filter(F.to == "create_confirm"))
async def edit_categories_create(callback: CallbackQuery, state: FSMContext, callback_data: NavCB, db: Database, budget_id):
    data = await state.get_data()
    await db.add_category(data["category_name"],budget_id, 0,data["sort_order"],callback_data.kind)
    text = await build_edit_screen(db, budget_id, Categories.ADDED.format(name=data["category_name"]),callback_data.kind)
    await callback.message.answer(text, reply_markup=confirm("edit_cat","edit",callback_data.kind))


@router.callback_query(NavCB.filter(F.to == "rename_confirm"))
async def edit_categories_rename(callback: CallbackQuery, state: FSMContext, callback_data: NavCB, db: Database, budget_id):
    data = await state.get_data()
    await db.rename_category(data["category_id"],data["category_name"])
    await render_edit_screen(callback,db,budget_id,state,Categories.RENAMED.format(name=data["category_name"]),callback_data.kind)

@router.callback_query(NavCB.filter(F.to == "confirm_delete"))
async def edit_categories_delete(callback: CallbackQuery, state: FSMContext, callback_data: NavCB, db: Database, budget_id):
    data = await state.get_data()
    await db.delete_category(data["category_id"])
    await render_edit_screen(callback,db,budget_id,state,Categories.DELETED,callback_data.kind)



@router.callback_query(NavCB.filter(F.to == "edit_cat"))
async def edit_categories_cat(callback: CallbackQuery,state: FSMContext, db: Database,callback_data: NavCB, budget_id):
    text = await build_edit_screen(db, budget_id, "",callback_data.kind)
    await callback.message.edit_text(text=text+"\n\n"+Categories.ASK_NEW_NAME,reply_markup=cancel_kb("edit_cancel",callback_data.kind))
    await state.set_state(CategoryName.waiting_name)
    await state.update_data(mode="create", kind=callback_data.kind)

@router.callback_query(NavCB.filter(F.to.in_(EDIT_PURPOSE)))
async def open_category_picker(callback, callback_data: NavCB, db, budget_id):
    await render_categories_screen(callback, db, budget_id, EDIT_PURPOSE[callback_data.to], 1,callback_data.kind)

@router.callback_query(NavCB.filter(F.to == "edit_arch"))
async def edit_categories_arch(callback: CallbackQuery, callback_data: NavCB):
    await callback.message.edit_text(text=Categories.CHOOSE_ARCHIVE,reply_markup=edit_archived_kb(callback_data.kind))
    return

@router.callback_query(NavCB.filter(F.to == "create_max"))
async def edit_categories_max(callback: CallbackQuery,state: FSMContext,callback_data: NavCB):
    await state.set_state(CategoryMaxCreate.waiting_max_create)
    await state.update_data(kind=callback_data.kind)
    await callback.message.edit_text(text=Categories.ASK_MAX,reply_markup=cancel_kb("edit_cancel",callback_data.kind))



@router.callback_query(CategoryCB.filter(F.purpose.in_({"archive", "dearchive"})))
async def archive_category(callback: CallbackQuery, db: Database, state: FSMContext, callback_data: CategoryCB,budget_id):
    if callback_data.purpose == "archive":
        await db.archive_category(callback_data.id)
        await state.clear()
        text = await build_edit_screen(db, budget_id, Categories.DONE, callback_data.kind)
        await callback.message.edit_text(text, reply_markup=edit_kb(callback_data.kind))
    else:
        await db.dearchive_category(callback_data.id)
        await state.clear()
        text = await build_edit_screen(db, budget_id, Categories.DONE,callback_data.kind)
        await callback.message.edit_text(text, reply_markup=edit_kb(callback_data.kind))

@router.callback_query(CategoryCB.filter(F.purpose == "changename"))
async def rename_category(callback: CallbackQuery, state: FSMContext,callback_data: CategoryCB):
    await state.set_state(CategoryName.waiting_name)
    await state.update_data(mode="rename",category_id=callback_data.id,kind=callback_data.kind)
    await callback.message.edit_text(text=Categories.ASK_NEW_NAME,reply_markup=cancel_kb("edit_cancel",callback_data.kind))

@router.callback_query(CategoryCB.filter(F.purpose == "changemax"))
async def changemax_category(callback: CallbackQuery, state: FSMContext,callback_data: CategoryCB):
    await state.set_state(CategoryMax.waiting_max)
    await state.update_data(mode="",category_id=callback_data.id,kind=callback_data.kind)
    await callback.message.edit_text(text=Categories.ASK_MAX,reply_markup=cancel_kb("edit_cancel",callback_data.kind))


@router.callback_query(CategoryCB.filter(F.purpose == "delete"))
async def delete_category(callback: CallbackQuery,state:FSMContext,callback_data:CategoryCB):
    await state.update_data(category_id=callback_data.id,kind=callback_data.kind)
    await callback.message.edit_text(Categories.DELETE_CONFIRM, reply_markup=confirm("confirm_delete","edit",callback_data.kind))


@router.message(CategoryMaxCreate.waiting_max_create)
async def input_max_create(message: Message,state: FSMContext,db: Database,budget_id):
    if message.text is None:
        await message.answer(Errors.BAD_AMOUNT)
        return
    maximum = parse_amount(message.text)
    if maximum is None:
        await message.answer(Errors.BAD_AMOUNT)
        return
    data = await state.get_data()
    await db.add_category(data["category_name"],budget_id,maximum,data["sort_order"],data["kind"])
    text = await build_edit_screen(db, budget_id, Categories.ADDED.format(name=data["category_name"]),data["kind"])
    await message.answer(text, reply_markup=confirm("edit_cat","edit",data["kind"]))

@router.message(CategoryMax.waiting_max)
async def input_category_max(message: Message,state: FSMContext, db: Database, budget_id):
    if message.text is None:
        await message.answer(Errors.BAD_AMOUNT)
        return
    maximum = parse_amount(message.text)
    if maximum is None:
        await message.answer(Errors.BAD_AMOUNT)
        return
    data = await state.get_data()
    category_id = data["category_id"]
    await db.change_maximum(category_id,maximum)
    text = await build_edit_screen(db, budget_id, Categories.MAX_CHANGED,data["kind"])
    await message.answer(text, reply_markup=edit_kb(data["kind"]))

@router.message(CategoryName.waiting_name)
async def input_category_name(message: Message,state: FSMContext, db: Database, budget_id):
    category_name = html.escape((message.text or "").strip())
    if not category_name:
        await message.answer(Categories.EMPTY_NAME)
        return
    if len(category_name) > 15:
        category_name = category_name[:15]
    data = await state.get_data()
    mode = data["mode"]
    confirm_text = "rename_confirm"
    kind = data["kind"]
    if mode == "create":
        confirm_text = "create_confirm"
        sort_order = await db.get_maximum_sort_order(budget_id,kind) + 10
        await state.update_data(sort_order=sort_order)

    if await db.check_category_name(budget_id,category_name) is not None:
        await state.update_data(category_name=category_name)
        await message.answer(Categories.NAME_EXISTS, reply_markup=confirm(confirm_text,"edit_cancel",kind))

    elif await db.check_category_name_archived(budget_id,category_name) is not None:
        await state.update_data(category_name=category_name)
        await message.answer(Categories.NAME_EXISTS, reply_markup=confirm(confirm_text,"edit_cancel",kind))

    else:
        if mode == "create":
            await state.update_data(category_name=category_name)
            if kind == "expense":
                await message.answer(text=Categories.PROMPT_MAXIMUM,reply_markup=confirm("create_max","create_confirm",kind))
            else:
                await db.add_category(category_name, budget_id, 0, sort_order, kind)
                text = await build_edit_screen(db, budget_id, Categories.ADDED.format(name=category_name),
                                               kind)
                await message.answer(text, reply_markup=confirm("edit_cat", "edit", kind))

        else:
            await db.rename_category(data["category_id"], category_name)
            await state.clear()
            text = await build_edit_screen(db, budget_id, Categories.RENAMED.format(name=category_name),kind)
            await message.answer(text, reply_markup=edit_kb(kind))

@router.callback_query()
async def unhandled(callback: CallbackQuery, state: FSMContext):
    logger.warning("НЕ ПОЙМАН callback=%s state=%s user=%s", callback.data, await state.get_state(), callback.from_user.id)
    await callback.answer()

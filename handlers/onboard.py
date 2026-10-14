from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from callback import NavCB, OnboardCB
from db import Database
from keyboards import code_kb, confirm
from texts import Errors, Onboarding

from .screens import edit_text, show_menu


class JoinBudget(StatesGroup):
    waiting_code = State()

router = Router(name="onboard")

class OnboardBudget(StatesGroup):
    waiting_cat = State()
    waiting_max = State()

@router.callback_query(OnboardCB.filter(F.action == "create"))
async def create_budget(callback: CallbackQuery, db: Database, budget_id):
    if budget_id is None:
        await db.create_budget(callback.from_user.id)
    await edit_text(callback.message, Onboarding.CREATE_BUDGET, reply_markup=confirm("edit_cat","menu"))




@router.callback_query(OnboardCB.filter(F.action == "join"))
async def join_budget(callback: CallbackQuery, state: FSMContext):
    await state.set_state(JoinBudget.waiting_code)
    await edit_text(callback.message, Onboarding.ADD_CODE_TEXT)

@router.message(JoinBudget.waiting_code)
async def join_code_budget(message: Message, db: Database,state: FSMContext,user):
    if message.text is None:
        await message.answer(Onboarding.NO_SUCH_BUDGET)
        return
    budget_id = await db.check_invite_code(message.text.strip())
    if budget_id is None:
        await message.answer(Onboarding.NO_SUCH_BUDGET)
        return
    await db.add_to_budget(user["user_id"],budget_id)
    await state.clear()
    await message.answer(Onboarding.JOINED)
    await show_menu(message, edit=False)

@router.callback_query(NavCB.filter(F.to == "code"))
async def get_code(callback:CallbackQuery,db: Database, budget_id):
    if budget_id is None:
        await edit_text(callback.message, Errors.NO_BUDGET)
        return
    code = await db.get_invite_code(budget_id)
    await edit_text(callback.message, Onboarding.GET_CODE_TEXT+f"<code>{code}</code>", reply_markup=code_kb())

@router.callback_query(NavCB.filter(F.to == "rotate_code"))
async def rotate_code(callback:CallbackQuery,db: Database, budget_id):
    if budget_id is None:
        await edit_text(callback.message, Errors.NO_BUDGET)
        return
    code = await db.rotate_invite_code(budget_id)
    await edit_text(
        callback.message, Onboarding.ROTATED_CODE_TEXT + f"<code>{code}</code>", reply_markup=code_kb()
    )

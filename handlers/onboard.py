from callback import OnboardCB,NavCB
from keyboards import main_menu,to_menu, confirm
from db import Database
from aiogram import F,Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from texts import CREATE_BUDGET, ADD_CODE_TEXT
from texts import GET_CODE_TEXT
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
    await callback.message.edit_text(CREATE_BUDGET, reply_markup=confirm("edit_cat","menu"))
    await callback.answer()




@router.callback_query(OnboardCB.filter(F.action == "join"))
async def join_budget(callback: CallbackQuery, state: FSMContext):
    await state.set_state(JoinBudget.waiting_code)
    await callback.message.edit_text(ADD_CODE_TEXT)

@router.message(JoinBudget.waiting_code)
async def join_code_budget(message: Message, db: Database,state: FSMContext,user):
    budget_id = await db.check_invite_code(message.text.strip())
    if budget_id is None:
        await message.edit_text("Такого бюджета нет")
        return
    await db.add_to_budget(user["user_id"],budget_id)
    await message.answer(f"Успешно присоединены!\nМеню",reply_markup=main_menu())

@router.callback_query(NavCB.filter(F.to == "code"))
async def get_code(callback:CallbackQuery,db: Database, budget_id):
    code = await db.get_invite_code(budget_id)
    await callback.message.edit_text(GET_CODE_TEXT+f"<code>{code}</code>",reply_markup=to_menu(),parse_mode="HTML")
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.callback_answer import CallbackAnswer

from callback import AddCB, CategoryCB, NavCB
from db import Database
from keyboards import added_confirm_kb, cancel_kb, date_expense_kb
from texts import Errors, Prompts, Stats
from utils import format_money, parse_amount_terms, parse_date, today
from validators import valid_kind, valid_mode

from .flow import require_flow
from .screens import build_categories_screen, edit_text, render_categories_screen

router = Router(name="expenses")

class AddExpense(StatesGroup):
    waiting_amount = State()
    waiting_date = State()

### Добавление траты
@router.callback_query(NavCB.filter(F.to.in_({"expense", "income"})))
async def choose_add_date(
    callback: CallbackQuery, state: FSMContext, db: Database, callback_data: NavCB, budget_id, user
):
    if budget_id is None:
        await callback.message.answer(Errors.NO_BUDGET)
        return
    now = datetime.now(ZoneInfo(user["timezone"])).strftime("%d/%m %H:%M")
    kind = callback_data.to  # the filter above already pins it to expense|income
    text = Prompts.CHOOSE_DATE_ADD[kind].format(now=now)
    await edit_text(callback.message, text, reply_markup=date_expense_kb(kind))


@router.callback_query(AddCB.filter())
async def start_add(callback: CallbackQuery, state: FSMContext, db: Database, callback_data: AddCB, budget_id,
                    callback_answer: CallbackAnswer):
    kind, mode = valid_kind(callback_data.kind), valid_mode(callback_data.mode)
    if kind is None or mode is None:
        callback_answer.text = Errors.BAD_SELECTION
        return
    await state.update_data(kind=kind, mode=mode)
    if mode == "date":
        await state.set_state(AddExpense.waiting_date)
        await edit_text(callback.message, Prompts.INPUT_DATE_ADD[kind], reply_markup=cancel_kb("menu"))
        return
    await render_categories_screen(callback, db, budget_id, purpose=kind, page=1, kind=kind, mode=mode)


@router.message(AddExpense.waiting_date)
async def data_entered(message:Message,state:FSMContext,db: Database,budget_id,tz):
    my_date = parse_date(message.text,tz)
    if my_date is None:
        await message.answer(Errors.BAD_DATE)
        return
    await state.update_data(my_date=my_date)
    data = await require_flow(state, message, "kind")
    if data is None:
        return
    kind = data["kind"]
    text, markup = await build_categories_screen(db, budget_id, purpose=kind, page=1, kind=kind, mode="date")
    await message.answer(text=text, reply_markup=markup)

### Сообщение при вводе трат, после ввода значения
@router.message(AddExpense.waiting_amount)
async def amount_entered(message: Message, state: FSMContext, db: Database, budget_id,tz):
    terms = parse_amount_terms(message.text)
    if terms is None:
        await message.answer(Errors.BAD_AMOUNT)
        return                                   # состояние НЕ сбрасываем
    amount = sum(terms)
    # parse_amount_terms allows "-50" (category maximums legitimately use 0/negative
    # via change_maximum/add_category), but a transaction amount must be positive --
    # the sign is applied at render time (views.py), not stored (BUG-7).
    if amount <= 0:
        await message.answer(Errors.BAD_AMOUNT)
        return
    data = await require_flow(state, message, "category_id", "mode")
    if data is None:
        return
    # my_date was parsed by data_entered two updates ago -- the one value of this flow
    # that can't ride on a button, so it's the one most likely to be gone.
    if data["mode"] == "date" and await require_flow(state, message, "my_date") is None:
        return
    kind = data.get("kind", "expense")
    # Attacker-crafted CategoryCB(id=<foreign category>) survives into FSM data here --
    # verify it still belongs to this budget before it can leak a foreign category name
    # into this budget's history (SEC-2).
    if not await db.category_in_budget(budget_id, data["category_id"]):
        await message.answer(Errors.NOT_FOUND)
        text, markup = await build_categories_screen(db, budget_id, purpose=kind, page=1, kind=kind)
        await message.answer(text=text, reply_markup=markup)
        return
    my_date = today(tz)
    if data["mode"] == "yesterday":
        my_date -= timedelta(days=1)
    if data["mode"] == "date":
        my_date = data["my_date"]
    ### несколько чеков за одну покупку ("100+250+80") -> одна запись на сумму 430
    await db.add_expense(budget_id, message.from_user.id, data["category_id"],
                     amount, my_date.isoformat(), kind)
    mode, my_date_kept = data["mode"], data.get("my_date")
    await state.clear()
    ### сохраняем дату/режим, чтобы следующая трата на эту же дату не спрашивала дату заново
    await state.update_data(mode=mode, my_date=my_date_kept, kind=kind)
    if len(terms) > 1:
        parts = " + ".join(format_money(t) for t in terms)
        text = Stats.ADDED_SUM.format(parts=parts, amount=format_money(amount))
    else:
        text = Stats.ADDED.format(amount=format_money(amount))
    await message.answer(text, reply_markup=added_confirm_kb(kind, mode))

### Сообщение при вводе трат, после выбора категории
@router.callback_query(CategoryCB.filter(F.purpose.in_({"expense", "income"})))
async def category_chosen(callback: CallbackQuery, callback_data: CategoryCB, state: FSMContext,
                          callback_answer: CallbackAnswer):
    # mode comes from the button itself, not from whatever is left in FSM state --
    # a concurrent "Меню" tap can state.clear() mid-flow and wipe a stale "mode" key (see traceback)
    if valid_mode(callback_data.mode) is None:
        callback_answer.text = Errors.BAD_SELECTION
        return
    # Fail at the tap, not one typed amount later: a "date" category button on a screen
    # older than the last state.clear() has no my_date behind it any more.
    if callback_data.mode == "date" and await require_flow(
        state, callback, "my_date", callback_answer=callback_answer
    ) is None:
        return
    await state.update_data(category_id=callback_data.id, kind=callback_data.purpose, mode=callback_data.mode)
    await state.set_state(AddExpense.waiting_amount)
    text = Prompts.AMOUNT[callback_data.purpose]
    await edit_text(callback.message, text)

### "Добавить ещё на эту дату" -> сразу к выбору категории, минуя выбор даты
@router.callback_query(NavCB.filter(F.to == "add_again"))
async def add_again(callback: CallbackQuery, state: FSMContext, db: Database, callback_data: NavCB, budget_id,
                    callback_answer: CallbackAnswer):
    # mode travels on the button itself (set from the add that was just completed), so this
    # no longer depends on FSM state surviving a concurrent "Меню" tap (see CategoryCB.mode)
    kind, mode = valid_kind(callback_data.kind), valid_mode(callback_data.mode)
    if kind is None or mode is None:
        callback_answer.text = Errors.BAD_SELECTION
        return
    # ...except the date itself for mode="date": a crafted nav:add_again:expense:date, or
    # a tap after a state.clear(), used to reach amount_entered and KeyError on my_date.
    if mode == "date" and await require_flow(
        state, callback, "my_date", callback_answer=callback_answer
    ) is None:
        return
    await state.update_data(mode=mode, kind=kind)
    await render_categories_screen(callback, db, budget_id, purpose=kind, page=1, kind=kind, mode=mode)


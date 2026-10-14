
from callback import AddCB, CategoryCB, NavCB
from db import Database
from handlers.expenses import (
    AddExpense,
    add_again,
    amount_entered,
    category_chosen,
    choose_add_date,
    data_entered,
)
from tests.fakes import (
    FakeCallbackQuery,
    FakeMessage,
    make_callback_answer,
    make_state,
    unpack_callback_data,
)
from texts import Errors


async def test_amount_entered_keeps_date_and_offers_add_again(db: Database) -> None:
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)
    cat_id = (await db.list_active_categories(budget_id, "expense"))[0]["category_id"]

    state = make_state()
    await state.update_data(mode="today", kind="expense", category_id=cat_id)
    message = FakeMessage(text="100", user_id=111)

    await amount_entered(message, state, db, budget_id, "Europe/Chisinau")

    data = await state.get_data()
    assert data["mode"] == "today"    # дата/режим сохранены, а не сброшены
    assert "category_id" not in data  # но выбор категории/суммы — не переносится

    markup = message.answer.await_args.kwargs["reply_markup"]
    btn_cb = unpack_callback_data(markup, 0, 0, NavCB)
    assert btn_cb == NavCB(to="add_again", kind="expense")


async def test_amount_entered_offers_add_on_other_date(db: Database) -> None:
    """The second button reuses main_menu()'s "➖ Трата"/"➕ Доход" callback_data, so it
    lands in choose_add_date -- the date picker -- for the same kind that was just added."""
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)

    for kind in ("expense", "income"):
        cat_id = (await db.list_active_categories(budget_id, kind))[0]["category_id"]
        state = make_state()
        await state.update_data(mode="yesterday", kind=kind, category_id=cat_id)
        message = FakeMessage(text="100", user_id=111)

        await amount_entered(message, state, db, budget_id, "Europe/Chisinau")

        markup = message.answer.await_args.kwargs["reply_markup"]
        other_date_cb = unpack_callback_data(markup, 1, 0, NavCB)
        assert other_date_cb == NavCB(to=kind)

        callback = FakeCallbackQuery(user_id=111)
        user = {"timezone": "Europe/Chisinau"}
        await choose_add_date(callback, state, db, other_date_cb, budget_id, user)

        date_markup = callback.message.edit_text.await_args.kwargs["reply_markup"]
        modes = [unpack_callback_data(date_markup, row, 0, AddCB) for row in range(3)]
        assert modes == [AddCB(mode=m, kind=kind) for m in ("today", "yesterday", "date")]


async def test_data_entered_rejects_non_text(db: Database) -> None:
    """BUG-4: a sticker/photo at the date prompt gives message.text=None --
    parse_date used to be called unguarded and raise AttributeError."""
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)

    state = make_state()
    await state.set_state(AddExpense.waiting_date)
    await state.update_data(kind="expense")
    message = FakeMessage(text=None, user_id=111)

    await data_entered(message, state, db, budget_id, "Europe/Chisinau")

    message.answer.assert_awaited_once_with(Errors.BAD_DATE)


async def test_amount_entered_rejects_negative_and_zero(db: Database) -> None:
    """BUG-7: parse_amount_terms accepts a leading '-' (it's shared with category-maximum
    input, where 0/negative are legal), but a stored transaction amount must be positive --
    the sign is meant to be applied at render time, not stored."""
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)
    cat_id = (await db.list_active_categories(budget_id, "expense"))[0]["category_id"]

    for text in ("-50", "0"):
        state = make_state()
        await state.update_data(mode="today", kind="expense", category_id=cat_id)
        message = FakeMessage(text=text, user_id=111)

        await amount_entered(message, state, db, budget_id, "Europe/Chisinau")

        message.answer.assert_awaited_once_with(Errors.BAD_AMOUNT)

    rows = await db.list_recent_transactions(budget_id, limit=10, offset=0)
    assert len(rows) == 0


async def test_add_again_skips_date_prompt_and_reuses_same_date(db: Database) -> None:
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)
    cats = await db.list_active_categories(budget_id, "expense")

    state = make_state()
    await state.update_data(mode="today", kind="expense", category_id=cats[0]["category_id"])
    message1 = FakeMessage(text="100", user_id=111)
    await amount_entered(message1, state, db, budget_id, "Europe/Chisinau")

    # "Добавить ещё на эту дату" -> напрямую к выбору категории, без повторного запроса даты
    callback = FakeCallbackQuery(user_id=111)
    await add_again(
        callback, state, db, NavCB(to="add_again", kind="expense"), budget_id, make_callback_answer()
    )
    callback.message.edit_text.assert_awaited_once()  # экран категорий, не запрос даты

    cat_cb = CategoryCB(id=cats[1]["category_id"], purpose="expense", kind="expense")
    await category_chosen(callback, cat_cb, state, make_callback_answer())

    message2 = FakeMessage(text="50", user_id=111)
    await amount_entered(message2, state, db, budget_id, "Europe/Chisinau")

    rows = await db.list_recent_transactions(budget_id, limit=10, offset=0)
    assert len(rows) == 2
    assert rows[0]["date"] == rows[1]["date"]  # одна и та же дата у обоих добавлений


async def test_amount_entered_plus_inserts_one_summed_row(db: Database) -> None:
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)
    cat_id = (await db.list_active_categories(budget_id, "expense"))[0]["category_id"]

    state = make_state()
    await state.update_data(mode="today", kind="expense", category_id=cat_id)
    message = FakeMessage(text="100+250", user_id=111)

    await amount_entered(message, state, db, budget_id, "Europe/Chisinau")

    rows = await db.list_recent_transactions(budget_id, limit=10, offset=0)
    assert len(rows) == 1                  # один чек с несколькими слагаемыми -> одна запись
    assert rows[0]["amount"] == 35000

    text = message.answer.await_args.args[0]
    assert "100 + 250" in text              # видно, что именно сложили, до подтверждения


async def test_add_again_falls_back_to_menu_on_stale_state(db: Database) -> None:
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)

    state = make_state()  # пустой state — сессия "устарела"
    callback = FakeCallbackQuery(user_id=111)

    await add_again(
        callback, state, db, NavCB(to="add_again", kind="expense"), budget_id, make_callback_answer()
    )

    callback.message.edit_text.assert_awaited_once()

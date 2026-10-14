"""Multi-step flows survive the three ways FSM data goes missing between two updates
(postmortems/2026-10-05-add-expense-mode-keyerror.md):

  (A) concurrency -- two updates of one user interleaving. Closed by
      SimpleEventIsolation in bot.py; pinned here statically, since bot.py can't be
      imported in tests (it reads .env and builds a Bot).
  (B) a state.clear() ("Меню", /cancel, archive...) between the writer and the reader,
      then a stale button tap or typed reply. Each chain below runs writer -> clear ->
      reader and expects the recovery path, not an exception.
  (C) hand-crafted callback data -- values no rendered button ever carried.
"""
import ast
from pathlib import Path

from aiogram.types import Chat, InaccessibleMessage

from callback import AddCB, CategoryCB, CatPageCB, NavCB
from db import Database
from handlers.common import display_pages_cat
from handlers.edit import (
    delete_category,
    edit_categories_arch,
    edit_categories_cat,
    edit_categories_create,
    edit_categories_delete,
    edit_categories_rename,
    input_category_max,
    input_category_name,
    input_max_create,
    rename_category,
)
from handlers.expenses import add_again, amount_entered, category_chosen, data_entered, start_add
from handlers.screens import show_menu
from tests.fakes import (
    FakeCallbackQuery,
    FakeMessage,
    make_callback_answer,
    make_state,
    unpack_callback_data,
)
from texts import Errors

REPO_ROOT = Path(__file__).resolve().parent.parent
TZ = "Europe/Chisinau"


async def _setup(db: Database):
    await db.ensure_user(111)
    budget_id = await db.create_budget(111)
    cats = await db.list_active_categories(budget_id, "expense")
    return budget_id, cats


async def _assert_expired_by_message(message: FakeMessage, state) -> None:
    message.answer.assert_any_await(Errors.FLOW_EXPIRED)
    message.answer_rich.assert_awaited_once()  # the menu, as a new message
    assert await state.get_state() is None


async def _assert_expired_by_callback(callback: FakeCallbackQuery, callback_answer, state) -> None:
    assert callback_answer.text == Errors.FLOW_EXPIRED
    callback.message.edit_text.assert_awaited()  # the menu, in place
    assert await state.get_state() is None


# --- (A) -----------------------------------------------------------------------------

def test_dispatcher_isolates_events_per_user() -> None:
    tree = ast.parse((REPO_ROOT / "bot.py").read_text(encoding="utf-8"))
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Dispatcher"
    ]
    assert len(calls) == 1
    assert "events_isolation" in {kw.arg for kw in calls[0].keywords}


# --- (B) add expense ---------------------------------------------------------------------

async def test_amount_after_clear_expires_instead_of_keyerror(db: Database) -> None:
    budget_id, cats = await _setup(db)
    state = make_state()

    callback = FakeCallbackQuery(user_id=111)
    cat_cb = CategoryCB(id=cats[0]["category_id"], purpose="expense", kind="expense", mode="today")
    await category_chosen(callback, cat_cb, state, make_callback_answer())
    await state.clear()  # "Меню" tapped while the amount prompt was open

    message = FakeMessage(text="100", user_id=111)
    await amount_entered(message, state, db, budget_id, TZ)

    await _assert_expired_by_message(message, state)
    assert await db.list_recent_transactions(budget_id, limit=10, offset=0) == []


async def test_amount_for_date_mode_without_date_expires(db: Database) -> None:
    """The "Still not covered" case of the postmortem: mode="date" survived, my_date didn't."""
    budget_id, cats = await _setup(db)
    state = make_state()
    await state.update_data(category_id=cats[0]["category_id"], mode="date", kind="expense")

    message = FakeMessage(text="100", user_id=111)
    await amount_entered(message, state, db, budget_id, TZ)

    await _assert_expired_by_message(message, state)
    assert await db.list_recent_transactions(budget_id, limit=10, offset=0) == []


async def test_date_category_tap_after_clear_expires_at_the_tap(db: Database) -> None:
    budget_id, cats = await _setup(db)
    state = make_state()

    start_cb = FakeCallbackQuery(user_id=111)
    date_cb = AddCB(mode="date", kind="expense")
    await start_add(start_cb, state, db, date_cb, budget_id, make_callback_answer())
    await data_entered(FakeMessage(text="01.10", user_id=111), state, db, budget_id, TZ)
    await state.clear()

    callback = FakeCallbackQuery(user_id=111)
    callback_answer = make_callback_answer()
    cat_cb = CategoryCB(id=cats[0]["category_id"], purpose="expense", kind="expense", mode="date")
    await category_chosen(callback, cat_cb, state, callback_answer)

    await _assert_expired_by_callback(callback, callback_answer, state)


async def test_date_typed_after_clear_expires(db: Database) -> None:
    budget_id, _ = await _setup(db)
    state = make_state()  # no "kind" -- start_add's write is gone

    message = FakeMessage(text="01.10", user_id=111)
    await data_entered(message, state, db, budget_id, TZ)

    await _assert_expired_by_message(message, state)


# --- (B) edit categories -----------------------------------------------------------------

async def test_create_name_after_clear_expires(db: Database) -> None:
    budget_id, _ = await _setup(db)
    state = make_state()

    open_cb = FakeCallbackQuery(user_id=111)
    await edit_categories_cat(open_cb, state, db, NavCB(to="edit_cat"), budget_id)
    await state.clear()

    message = FakeMessage(text="Новая", user_id=111)
    await input_category_name(message, state, db, budget_id)

    await _assert_expired_by_message(message, state)


async def test_create_confirm_after_clear_expires(db: Database) -> None:
    budget_id, cats = await _setup(db)
    state = make_state()

    open_cb = FakeCallbackQuery(user_id=111)
    await edit_categories_cat(open_cb, state, db, NavCB(to="edit_cat"), budget_id)
    await input_category_name(FakeMessage(text="Новая", user_id=111), state, db, budget_id)
    await state.clear()

    callback = FakeCallbackQuery(user_id=111)
    callback_answer = make_callback_answer()
    yes_cb = NavCB(to="create_confirm")
    await edit_categories_create(callback, state, yes_cb, db, budget_id, callback_answer)

    await _assert_expired_by_callback(callback, callback_answer, state)
    assert len(await db.list_active_categories(budget_id, "expense")) == len(cats)


async def test_create_maximum_after_clear_expires(db: Database) -> None:
    budget_id, cats = await _setup(db)
    state = make_state()  # category_name/sort_order from the name step are gone

    message = FakeMessage(text="500", user_id=111)
    await input_max_create(message, state, db, budget_id)

    await _assert_expired_by_message(message, state)
    assert len(await db.list_active_categories(budget_id, "expense")) == len(cats)


async def test_change_maximum_after_clear_expires(db: Database) -> None:
    budget_id, _ = await _setup(db)
    state = make_state()

    message = FakeMessage(text="500", user_id=111)
    await input_category_max(message, state, db, budget_id)

    await _assert_expired_by_message(message, state)


async def test_rename_confirm_after_clear_expires(db: Database) -> None:
    """The id is on the "Да" button now, but the typed name still lives in FSM."""
    budget_id, cats = await _setup(db)
    state = make_state()
    target = CategoryCB(id=cats[0]["category_id"], purpose="changename", kind="expense")

    await rename_category(FakeCallbackQuery(user_id=111), state, target)
    name_msg = FakeMessage(text=cats[1]["name"], user_id=111)  # collides -> confirm screen
    await input_category_name(name_msg, state, db, budget_id)
    yes_cb = unpack_callback_data(name_msg.answer.await_args.kwargs["reply_markup"], 0, 0, CategoryCB)
    assert yes_cb.id == cats[0]["category_id"] and yes_cb.purpose == "rename_confirm"
    await state.clear()

    callback = FakeCallbackQuery(user_id=111)
    callback_answer = make_callback_answer()
    await edit_categories_rename(callback, state, yes_cb, db, budget_id, callback_answer)

    await _assert_expired_by_callback(callback, callback_answer, state)
    names = [c["name"] for c in await db.list_active_categories(budget_id, "expense")]
    assert names.count(cats[1]["name"]) == 1  # nothing renamed


async def test_delete_confirm_survives_clear(db: Database) -> None:
    """Before 1.6.0 the id sat in FSM and a clear in between made "Да" crash.
    It rides on the button now, so the delete just goes through."""
    budget_id, cats = await _setup(db)
    state = make_state()
    ask = FakeCallbackQuery(user_id=111)

    await delete_category(ask, CategoryCB(id=cats[0]["category_id"], purpose="delete"))
    markup = ask.message.edit_text.await_args.kwargs["reply_markup"]
    yes_cb = unpack_callback_data(markup, 0, 0, CategoryCB)
    await state.clear()

    callback_answer = make_callback_answer()
    callback = FakeCallbackQuery(user_id=111)
    await edit_categories_delete(callback, state, yes_cb, db, budget_id, callback_answer)

    assert callback_answer.text is None
    ids = [c["category_id"] for c in await db.list_active_categories(budget_id, "expense")]
    assert cats[0]["category_id"] not in ids


# --- (C) crafted callback data -------------------------------------------------------------

async def test_crafted_add_again_date_on_empty_state_expires(db: Database) -> None:
    """Was a live KeyError: 'my_date' -- nav:add_again:expense:date with no date ever entered."""
    budget_id, _ = await _setup(db)
    state = make_state()
    callback = FakeCallbackQuery(user_id=111)
    callback_answer = make_callback_answer()

    crafted = NavCB(to="add_again", kind="expense", mode="date")
    await add_again(callback, state, db, crafted, budget_id, callback_answer)

    await _assert_expired_by_callback(callback, callback_answer, state)


async def test_crafted_out_of_domain_values_are_rejected(db: Database) -> None:
    budget_id, cats = await _setup(db)
    cat_id = cats[0]["category_id"]
    cases = [
        lambda cb, st, ca: add_again(cb, st, db, NavCB(to="add_again", kind="expense", mode="x"),
                                     budget_id, ca),
        lambda cb, st, ca: add_again(cb, st, db, NavCB(to="add_again", kind="x"), budget_id, ca),
        lambda cb, st, ca: start_add(cb, st, db, AddCB(mode="x", kind="expense"), budget_id, ca),
        lambda cb, st, ca: start_add(cb, st, db, AddCB(mode="today", kind="x"), budget_id, ca),
        lambda cb, st, ca: category_chosen(cb, CategoryCB(id=cat_id, purpose="expense", mode="x"),
                                           st, ca),
        lambda cb, st, ca: display_pages_cat(cb, db, CatPageCB(page=1, purpose="expense", kind="x"),
                                             budget_id, ca),
    ]
    for run in cases:
        state = make_state()
        callback = FakeCallbackQuery(user_id=111)
        callback_answer = make_callback_answer()

        await run(callback, state, callback_answer)

        assert callback_answer.text == Errors.BAD_SELECTION
        callback.message.edit_text.assert_not_awaited()
        assert await state.get_data() == {}  # nothing out-of-domain made it into FSM


# --- callback.message is None / InaccessibleMessage ---------------------------------------

async def test_screens_skip_messages_that_cannot_be_edited() -> None:
    """None = inline-mode button, InaccessibleMessage = a message Telegram no longer gives the bot. Both
    used to be an AttributeError inside edit_text, reported as "Что-то сломалось"."""
    inaccessible = InaccessibleMessage(chat=Chat(id=1, type="private"), message_id=1)
    for message in (None, inaccessible):
        callback = FakeCallbackQuery(user_id=111, message=message)
        await edit_categories_arch(callback, NavCB(to="edit_arch"))  # edit_text
        await show_menu(callback.message, edit=True)  # edit_rich
        await show_menu(callback.message, edit=False)  # answer_rich

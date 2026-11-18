"""Bulk import from a JSON file: parser (importer.py), DB batch/undo, handlers, routing."""
import io
import json
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.types import Chat, Document, Message, User

from expenses_bot import importer
from expenses_bot.handlers import importer as h
from expenses_bot.handlers.expenses import AddExpense
from expenses_bot.ui.callback import ImportCB
from tests.fakes import FakeCallbackQuery, FakeMessage, make_callback_answer, make_state

TODAY = date(2026, 11, 18)
# Handlers use the real today(tz), so their files need a date relative to the real clock.
RECENT = (date.today() - timedelta(days=2)).isoformat()
CATS = {"expense": {"Продукты": 1, "Кафе &amp; бары": 2}, "income": {"Зарплата": 3}}


def _file(*transactions, **top) -> bytes:
    return json.dumps({"version": 1, "transactions": list(transactions), **top}).encode()


def _tx(**kw) -> dict:
    return {"date": "2026-11-01", "kind": "expense", "category": "Продукты", "amount": "100", **kw}


# --- parser -----------------------------------------------------------------

def test_valid_file_parses_all_rows() -> None:
    res = importer.parse_import(
        _file(_tx(amount="123.45"), _tx(kind="income", category="Зарплата", amount=5000)), CATS, TODAY
    )
    assert res.errors == []
    assert res.rows == [
        importer.ImportRow("2026-11-01", "expense", 1, 12345),
        importer.ImportRow("2026-11-01", "income", 3, 500000),
    ]


def test_escaped_stored_name_matches_visible_name_case_insensitive() -> None:
    res = importer.parse_import(_file(_tx(category=" кафе & БАРЫ ")), CATS, TODAY)
    assert res.errors == [] and res.rows[0].category_id == 2


def test_bom_is_tolerated() -> None:
    assert importer.parse_import(b"\xef\xbb\xbf" + _file(_tx()), CATS, TODAY).errors == []


def test_garbage_and_wrong_shape_rejected() -> None:
    for raw in (b"not json", b"\xff\xfe", b"[]", b'{"transactions": {}}', _file(), _file(_tx(), version=2)):
        res = importer.parse_import(raw, CATS, TODAY)
        assert res.errors and not res.rows, raw


def test_one_bad_row_rejects_whole_file() -> None:
    res = importer.parse_import(_file(_tx(), _tx(category="Кофе")), CATS, TODAY)
    assert res.rows == []
    assert len(res.errors) == 1 and "запись 2" in res.errors[0] and "Кофе" in res.errors[0]


def test_category_of_other_kind_rejected() -> None:
    assert importer.parse_import(_file(_tx(category="Зарплата")), CATS, TODAY).errors


def test_dates_bounds() -> None:
    future = (TODAY + timedelta(days=1)).isoformat()
    old = (TODAY - timedelta(days=importer.MAX_AGE_DAYS + 1)).isoformat()
    for bad in (future, old, "01.11.2026", "2026-02-30", None):
        assert importer.parse_import(_file(_tx(date=bad)), CATS, TODAY).errors, bad
    assert importer.parse_import(_file(_tx(date=TODAY.isoformat())), CATS, TODAY).errors == []


def test_amount_formats() -> None:
    good = {"12,5": 1250, "12.50": 1250, 12.5: 1250, 7: 700, " 3 ": 300}
    for value, kopeks in good.items():
        res = importer.parse_import(_file(_tx(amount=value)), CATS, TODAY)
        assert res.rows and res.rows[0].amount == kopeks, value
    for value in ("0", 0, "-5", -5, "1.234", "abc", True, None, [1], "1e5", 10**12):
        assert importer.parse_import(_file(_tx(amount=value)), CATS, TODAY).errors, value


def test_unknown_kind_and_non_object_rows() -> None:
    assert importer.parse_import(_file(_tx(kind="transfer")), CATS, TODAY).errors
    assert importer.parse_import(_file("строка"), CATS, TODAY).errors


def test_too_many_rows() -> None:
    res = importer.parse_import(_file(*[_tx()] * (importer.MAX_ROWS + 1)), CATS, TODAY)
    assert res.errors and not res.rows


def test_digest_ignores_order_but_not_content() -> None:
    a = importer.ImportRow("2026-11-01", "expense", 1, 100)
    b = importer.ImportRow("2026-11-02", "expense", 1, 200)
    assert importer.digest([a, b]) == importer.digest([b, a])
    assert importer.digest([a]) != importer.digest([a, b])


def test_schema_lists_categories_and_example_validates() -> None:
    names = {"expense": ["Продукты", "Кафе & бары"], "income": ["Зарплата"]}
    schema = importer.build_schema(names, TODAY)
    variants = schema["properties"]["transactions"]["items"]["oneOf"]
    assert [v["properties"]["category"]["enum"] for v in variants] == [names["expense"], names["income"]]
    # The example we hand the AI must itself pass our own parser.
    example = json.dumps(importer.example(names, TODAY)).encode()
    assert importer.parse_import(example, CATS, TODAY).errors == []


# --- DB ---------------------------------------------------------------------

async def _budget(db, user_id=1):
    await db.ensure_user(user_id)
    budget_id = await db.create_budget(user_id)
    cats = await h._categories(db, budget_id)
    return budget_id, cats


async def _count(db, budget_id):
    return await db.count_transactions(budget_id)


async def test_create_import_is_atomic_dedup_and_undoable(db) -> None:
    budget_id, cats = await _budget(db)
    cid = next(iter(cats["expense"].values()))
    rows = [importer.ImportRow("2026-11-01", "expense", cid, 100 * i) for i in range(1, 4)]
    digest = importer.digest(rows)

    import_id = await db.create_import(budget_id, 1, digest, rows)
    assert import_id is not None and await _count(db, budget_id) == 3
    assert (await db.find_import(budget_id, digest))["row_count"] == 3

    assert await db.create_import(budget_id, 1, digest, rows) is None   # duplicate
    assert await _count(db, budget_id) == 3

    await db.add_expense(budget_id, 1, cid, 999, "2026-11-02")          # a manual one survives undo
    assert await db.delete_import(budget_id, import_id) == 1
    assert await _count(db, budget_id) == 1
    assert await db.find_import(budget_id, digest) is None


async def test_undo_scoped_to_own_budget(db) -> None:
    budget_a, cats = await _budget(db, 1)
    budget_b, _ = await _budget(db, 2)
    cid = next(iter(cats["expense"].values()))
    rows = [importer.ImportRow("2026-11-01", "expense", cid, 100)]
    import_id = await db.create_import(budget_a, 1, importer.digest(rows), rows)
    assert await db.get_import(budget_b, import_id) is None
    assert await db.delete_import(budget_b, import_id) == 0
    assert await _count(db, budget_a) == 1


async def test_migration_sets_user_version_4(db) -> None:
    async with db.conn.execute("PRAGMA user_version") as cur:
        assert (await cur.fetchone())[0] == 4


# --- handlers ---------------------------------------------------------------

def _doc_message(name="import.json", size=100):
    message = FakeMessage()
    message.document = SimpleNamespace(file_name=name, file_size=size)
    return message


def _bot(raw: bytes):
    return SimpleNamespace(download=AsyncMock(return_value=io.BytesIO(raw)))


async def _send(db, raw, budget_id, state=None, name="import.json"):
    message, state = _doc_message(name), state or make_state()
    await h.import_file(message, state, _bot(raw), db, budget_id, "Europe/Chisinau")
    return message, state


async def test_file_to_preview_to_commit_to_undo(db) -> None:
    budget_id, _ = await _budget(db)
    raw = _file(_tx(date=RECENT, amount="10"), _tx(date=RECENT, amount="20"))
    message, state = await _send(db, raw, budget_id)
    assert "Нашёл 2 записей" in message.answer.await_args.args[0]
    assert await state.get_state() == h.ImportFlow.confirm.state

    cb, answer = FakeCallbackQuery(), make_callback_answer()
    await h.import_commit(cb, state, db, budget_id, answer)
    assert await _count(db, budget_id) == 2
    assert await state.get_data() == {}
    markup = cb.message.edit_text.await_args.kwargs["reply_markup"]
    undo = ImportCB.unpack(markup.inline_keyboard[0][0].callback_data)
    assert undo.action == "undo_ask"

    # Same file again -> recognised as a duplicate before the preview.
    message, state = await _send(db, raw, budget_id)
    assert "уже загружен" in message.answer.await_args.args[0]
    assert await state.get_state() is None

    await h.import_undo(FakeCallbackQuery(), ImportCB(action="undo", id=undo.id), db, budget_id,
                        make_callback_answer())
    assert await _count(db, budget_id) == 0
    second = make_callback_answer()
    await h.import_undo(FakeCallbackQuery(), ImportCB(action="undo", id=undo.id), db, budget_id, second)
    assert second.text  # "already undone" toast, no crash


async def test_bad_file_reports_escaped_errors_and_writes_nothing(db) -> None:
    budget_id, _ = await _budget(db)
    message, state = await _send(db, _file(_tx(date=RECENT, category="<b>Кофе</b>")), budget_id)
    text = message.answer.await_args.args[0]
    assert "&lt;b&gt;" in text and "<b>Кофе" not in text
    assert await state.get_state() is None and await _count(db, budget_id) == 0


async def test_non_json_and_oversized_rejected_without_download(db) -> None:
    budget_id, _ = await _budget(db)
    for message in (_doc_message("photo.jpg"), _doc_message(size=importer.MAX_FILE_BYTES + 1)):
        bot = _bot(b"")
        await h.import_file(message, make_state(), bot, db, budget_id, "Europe/Chisinau")
        bot.download.assert_not_awaited()
        message.answer.assert_awaited_once()


async def test_commit_after_menu_is_expired(db) -> None:
    budget_id, _ = await _budget(db)
    _, state = await _send(db, _file(_tx(date=RECENT)), budget_id)
    await state.clear()  # "Меню"
    answer = make_callback_answer()
    await h.import_commit(FakeCallbackQuery(), state, db, budget_id, answer)
    assert answer.text and await _count(db, budget_id) == 0


async def test_commit_rechecks_categories(db) -> None:
    budget_id, cats = await _budget(db)
    _, state = await _send(db, _file(_tx(date=RECENT)), budget_id)
    await db.archive_category(budget_id, cats["expense"]["Продукты"])
    await h.import_commit(FakeCallbackQuery(), state, db, budget_id, make_callback_answer())
    assert await _count(db, budget_id) == 0


async def test_document_beats_waiting_amount_in_routing(dispatcher, db) -> None:
    """Router order: a file sent mid add-expense must reach import_file, not amount_entered."""
    budget_id, _ = await _budget(db)
    state = make_state()
    await state.set_state(AddExpense.waiting_amount)
    message = Message(
        message_id=1, date=0, chat=Chat(id=1, type="private"),
        from_user=User(id=1, is_bot=False, first_name="t"),
        document=Document(file_id="f", file_unique_id="u", file_name="x.json", file_size=10),
    )
    bot = _bot(b"not json")
    try:
        await dispatcher.propagate_event(
            "message", message, state=state, bot=bot, db=db, budget_id=budget_id, tz="Europe/Chisinau",
        )
    except RuntimeError as error:  # message.answer() without a mounted Bot
        assert "mount" in str(error)
    bot.download.assert_awaited_once()
    assert await state.get_state() is None

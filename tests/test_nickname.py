import tempfile
from pathlib import Path

from db import Database
from handlers.settings import Settings, nickname_entered
from tests.fakes import FakeMessage, make_state


async def test_set_nickname_round_trip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        await db.connect()
        user = await db.ensure_user(111)
        assert user["nickname"] == ""

        await db.set_nickname(111, "Vasya")
        user = await db.ensure_user(111)
        assert user["nickname"] == "Vasya"

        await db.close()


async def test_whitespace_only_nickname_rejected() -> None:
    """Whitespace-only input must not be saved — re-prompt instead of persisting blank."""
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        await db.connect()
        user = await db.ensure_user(111)

        state = make_state()
        await state.set_state(Settings.waiting_nickname)
        message = FakeMessage(text="   ")

        await nickname_entered(message, state, db, user)

        message.answer.assert_awaited_once()
        assert (await db.ensure_user(111))["nickname"] == ""
        assert await state.get_state() == Settings.waiting_nickname.state  # not cleared

        await db.close()


async def test_valid_nickname_saved_and_state_cleared() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        await db.connect()
        user = await db.ensure_user(111)

        state = make_state()
        await state.set_state(Settings.waiting_nickname)
        message = FakeMessage(text="Вася")

        await nickname_entered(message, state, db, user)

        assert (await db.ensure_user(111))["nickname"] == "Вася"
        assert await state.get_state() is None

        await db.close()


async def test_long_nickname_is_truncated() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        await db.connect()
        user = await db.ensure_user(111)

        state = make_state()
        await state.set_state(Settings.waiting_nickname)
        message = FakeMessage(text="а" * 30)

        await nickname_entered(message, state, db, user)

        saved = (await db.ensure_user(111))["nickname"]
        assert len(saved) == 20

        await db.close()
        print("nickname ✓")

import tempfile
from pathlib import Path

from db import Database


async def test_migrations_idempotent() -> None:
    """Повторное подключение к той же базе не должно падать на миграциях."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.db"
        async with Database(path):
            pass

        async with Database(path):          # миграции уже применены — не должны выполниться повторно
            pass
        print("migrations ✓")

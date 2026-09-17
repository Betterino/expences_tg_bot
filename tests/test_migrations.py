import tempfile
from pathlib import Path

from db import Database


async def test_migrations_idempotent() -> None:
    """Повторное подключение к той же базе не должно падать на миграциях."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.db"
        db1 = Database(path)
        await db1.connect()
        await db1.close()

        db2 = Database(path)
        await db2.connect()          # миграции уже применены — не должны выполниться повторно
        await db2.close()
        print("migrations ✓")

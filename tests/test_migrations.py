from db import Database


async def test_migrations_idempotent(tmp_path) -> None:
    """Повторное подключение к той же базе не должно падать на миграциях."""
    path = tmp_path / "test.db"
    async with Database(path):
        pass

    async with Database(path):          # миграции уже применены — не должны выполниться повторно
        pass

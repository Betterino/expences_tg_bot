from db import Database, backup_db


async def test_backup(tmp_path) -> None:
    db_path = tmp_path / "expenses.db"
    backup_dir = tmp_path / "backups"
    async with Database(db_path) as db:
        # --- бэкап создаёт файл ---
        dest = await backup_db(db, backup_dir)
        assert dest.exists()
        files = list(backup_dir.glob("expenses-*.db"))
        assert len(files) == 1

        # --- ротация: старые бэкапы удаляются, оставляя только последние `keep` ---
        for year in (2020, 2021, 2022):
            name = f"expenses-{year}-01-01_0000.db"
            (backup_dir / name).write_bytes(b"")
        await backup_db(db, backup_dir, keep=2)
        files = sorted(backup_dir.glob("expenses-*.db"), reverse=True)
        assert len(files) == 2, [f.name for f in files]
        assert files[0].name == dest.name  # самый свежий (только что созданный) сохранён

        # --- повторный вызов не падает на logger/asyncio NameError ---
        # (сам факт отсутствия исключения — проверка)
        await backup_db(db, backup_dir, keep=2)

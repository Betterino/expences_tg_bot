import aiosqlite
from pathlib import Path
import secrets
import asyncio
import logging

logger = logging.getLogger(__name__)

SCHEMA = """

CREATE TABLE IF NOT EXISTS budgets(
budget_id INTEGER PRIMARY KEY,
created_by INTEGER REFERENCES users(user_id),
type TEXT NOT NULL DEFAULT 'fixed',
invite_code TEXT UNIQUE );

CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
current_budget INTEGER DEFAULT NULL REFERENCES budgets(budget_id));

CREATE TABLE IF NOT EXISTS categories(
category_id INTEGER PRIMARY KEY,
name TEXT NOT NULL,
budget_id INTEGER REFERENCES budgets(budget_id) ON DELETE CASCADE, 
maximum INTEGER NOT NULL DEFAULT 0,
sort_order INTEGER DEFAULT 10,
is_archived INTEGER NOT NULL DEFAULT 0);

CREATE TABLE IF NOT EXISTS expenses(
expense_id INTEGER PRIMARY KEY, 
date TEXT NOT NULL, 
amount INTEGER NOT NULL, 
category_id INTEGER REFERENCES categories(category_id) ON DELETE SET NULL, 
budget_id INTEGER REFERENCES budgets(budget_id) ON DELETE CASCADE, 
added_by INTEGER REFERENCES users(user_id));
CREATE INDEX IF NOT EXISTS idx_expenses_period ON expenses(budget_id, date);


CREATE TABLE IF NOT EXISTS default_categories(
    name       TEXT PRIMARY KEY,
    sort_order INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO default_categories(name, sort_order) VALUES
    ('Продукты', 10),
    ('Здоровье', 20),
    ('Жилье и ЖКУ', 30),
    ('Транспорт', 40),
    ('Связь и подписки', 50),
    ('Кафе и рестораны', 60),
    ('Одежда', 70),
    ('Развлечения', 80),
    ('Прочее', 90);
"""

MIGRATIONS = [
    # версия 1
    "ALTER TABLE users ADD COLUMN timezone TEXT NOT NULL DEFAULT 'Europe/Chisinau';",
    """
    ALTER TABLE categories ADD COLUMN kind TEXT NOT NULL DEFAULT 'expense';
    ALTER TABLE expenses ADD COLUMN kind TEXT NOT NULL DEFAULT 'expense';
    ALTER TABLE default_categories ADD COLUMN kind TEXT NOT NULL DEFAULT 'expense';
    INSERT OR IGNORE INTO default_categories(name, sort_order, kind) VALUES
        ('Зарплата', 10, 'income'),
        ('Подработка', 20, 'income'),
        ('Подарки', 30, 'income'),
        ('Прочие доходы', 40, 'income');
    """,
    # версия 3
    "ALTER TABLE users ADD COLUMN nickname TEXT NOT NULL DEFAULT '';",
]



class Database:
    def __init__(self,path: Path):
        self.path = path
        self._conn: aiosqlite.Connection | None = None



    async def connect(self):
        self._conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.conn.execute("PRAGMA journal_mode = WAL")
        await self.conn.executescript(SCHEMA)
        await self._migrate()    
        await self.conn.commit()

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database.connect() не вызван")
        return self._conn

    async def _migrate(self):
        async with self.conn.execute("PRAGMA user_version") as cur:
            row = await cur.fetchone()
            assert row is not None
            version = row[0]

        for i, script in enumerate(MIGRATIONS[version:], start=version + 1):
            await self.conn.executescript(script)
            await self.conn.execute(f"PRAGMA user_version = {i}")
            await self.conn.commit()
            print(f"миграция {i} применена") 

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def add_expense(self, budget_id, user_id, category_id, amount, date,kind="expense"):
        cursor = await self.conn.execute(
            "INSERT INTO expenses (budget_id, added_by, category_id, amount, date,kind) "
            "VALUES (?, ?, ?, ?, ?,?)",
            (budget_id, user_id, category_id, amount, date,kind),
        )
        await self.conn.commit()
        return cursor.lastrowid

    async def add_category(self,name, budget_id,  maximum, sort_order, kind = "expense"):
        cursor = await self.conn.execute(
            "INSERT INTO categories (name,budget_id, maximum, sort_order, kind) "
            "VALUES (?, ?, ?, ?,?)",
            (name, budget_id, maximum, sort_order, kind),
        )
        await self.conn.commit()
        return cursor.lastrowid

    async def get_maximum_sort_order(self,budget_id,kind = "expense"):
        async with self.conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) as max FROM categories "
            "WHERE budget_id = ? AND is_archived = 0 AND kind = ?",
            (budget_id,kind,),
        ) as cursor:
            row = await cursor.fetchone()
        return row["max"] if row else None
    
    async def check_category_name(self,budget_id,name,kind = "expense"):
        async with self.conn.execute(
            "SELECT name FROM categories "
            "WHERE budget_id = ? AND name = ? AND is_archived = 0 AND kind = ?",
            (budget_id,name,kind),
        ) as cursor:
            row = await cursor.fetchone()
        return row
    
    async def check_category_name_archived(self,budget_id,name,kind = "expense"):
        async with self.conn.execute(
            "SELECT name FROM categories "
            "WHERE budget_id = ? AND name = ? AND kind = ?",
            (budget_id,name,kind,),
        ) as cursor:
            row = await cursor.fetchone()
        return row
    
    async def get_budget_type(self, budget_id):
        cursor = await self.conn.execute(
            "SELECT type FROM budgets WHERE budget_id = ?",
            (budget_id,),
        )
        return await cursor.fetchone()
    
    async def get_invite_code(self,budget_id):
        cursor = await self.conn.execute(
            "SELECT invite_code FROM budgets WHERE budget_id = ?",
            (budget_id,),
        )
        row = await cursor.fetchone()
        return row["invite_code"] if row else None
    
    async def check_invite_code(self,invite_code):
        cursor = await self.conn.execute(
            "SELECT budget_id FROM budgets WHERE invite_code = ?",
            (invite_code,),
        )
        row = await cursor.fetchone()
        return row["budget_id"] if row else None

    async def add_to_budget(self,user_id,budget_id):
        cursor = await self.conn.execute(
                    "UPDATE users SET current_budget = ? WHERE user_id = ?",(budget_id,user_id,),)
        await self.conn.commit()
        return cursor.lastrowid

    async def stats_total(self, budget_id, start, end, kind = "expense"):
        async with self.conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses "
            "WHERE budget_id = ? AND date BETWEEN ? AND ? AND kind = ?",
            (budget_id, start, end, kind),
        ) as cursor:
            row = await cursor.fetchone()
        return row["total"] if row else None
    
    async def ensure_user(self,user_id):
        await self.conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await self.conn.commit()
        async with self.conn.execute(
            "SELECT * FROM users "
            "WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row
    
    async def create_budget(self, user_id, budget_type="fixed"):
        cursor = await self.conn.execute(
            "INSERT INTO budgets (created_by, type, invite_code) VALUES (?, ?, ?)",
            (user_id, budget_type, secrets.token_urlsafe(8)),
        )
        budget_id = cursor.lastrowid
        await self.conn.execute(
            "INSERT INTO categories (name, budget_id,sort_order,kind) "
            "SELECT name, ?, sort_order, kind FROM default_categories",
            (budget_id,),
        )
        await self.conn.execute(
            "UPDATE users SET current_budget = ? WHERE user_id = ?", (budget_id, user_id)
        )
        await self.conn.commit()
        return budget_id
                 
    async def list_active_categories(self, budget_id,kind="expense"):
        async with self.conn.execute(
            "SELECT category_id, name FROM categories "
            "WHERE budget_id = ? AND is_archived = 0 AND kind = ? ORDER BY sort_order, category_id ",
            (budget_id,kind,),
        ) as cursor:
            return await cursor.fetchall()
    
    async def expense_by_category(self, budget_id, start, end):
        async with self.conn.execute(
            """SELECT   c.name AS name,
                        COALESCE(SUM(e.amount), 0) AS total,
                        c.maximum AS maximum
            FROM categories c
            LEFT JOIN expenses e ON e.category_id = c.category_id
                                AND e.date BETWEEN ? AND ?
            WHERE c.budget_id = ? AND (c.is_archived = 0 OR e.expense_id IS NOT NULL) AND c.kind = 'expense'
            GROUP BY c.category_id
            """,
            (start, end,budget_id,),
        ) as cursor:
            return await cursor.fetchall()
        
    async def income_by_category(self,budget_id,start,end):
        async with self.conn.execute(
            """SELECT   c.name AS name,
                        COALESCE(SUM(e.amount), 0) AS total,
                        c.maximum AS maximum
            FROM categories c
            LEFT JOIN expenses e ON e.category_id = c.category_id
                                AND e.date BETWEEN ? AND ?
            WHERE c.budget_id = ? AND (c.is_archived = 0 OR e.expense_id IS NOT NULL) AND c.kind = 'income'
            GROUP BY c.category_id
            """,
            (start, end,budget_id,),
        ) as cursor:
            return await cursor.fetchall()
        
    async def all_categories(self,budget_id,kind = "expense"):
        async with self.conn.execute(
            """SELECT   name,
                        maximum,
                        is_archived
            FROM categories
            WHERE budget_id = ? AND kind = ?
            ORDER BY sort_order
            """,
            (budget_id,kind,),
        ) as cursor:
            return await cursor.fetchall()

    async def list_archived_categories(self,budget_id,kind = "expense"):
        async with self.conn.execute(
            "SELECT category_id, name FROM categories "
            "WHERE budget_id = ? AND is_archived != 0 AND kind = ? ORDER BY sort_order, category_id ",
            (budget_id,kind),
        ) as cursor:
            return await cursor.fetchall()    

    async def list_all_categories(self,budget_id,kind = "expense"):
        async with self.conn.execute(
            "SELECT category_id, name, is_archived FROM categories "
            "WHERE budget_id = ? AND kind = ? ORDER BY is_archived, sort_order, category_id ",
            (budget_id,kind,),
        ) as cursor:
            return await cursor.fetchall() 

    async def archive_category(self,category_id):
        cursor = await self.conn.execute(
                    "UPDATE categories SET is_archived = 1 WHERE category_id = ?",(category_id,),)
        await self.conn.commit()
        return cursor.lastrowid
    
    async def dearchive_category(self,category_id):
        cursor = await self.conn.execute(
                    "UPDATE categories SET is_archived = 0 WHERE category_id = ?",(category_id,),)
        await self.conn.commit()
        return cursor.lastrowid
    
    async def rename_category(self,category_id,category_name):
        cursor = await self.conn.execute(
                    "UPDATE categories SET name = ? WHERE category_id = ?",(category_name,category_id,),)
        await self.conn.commit()
        return cursor.lastrowid

    async def change_maximum(self,category_id,maximum):
        cursor = await self.conn.execute(
                    "UPDATE categories SET maximum = ? WHERE category_id = ?",(maximum,category_id,),)
        await self.conn.commit()
        return cursor.lastrowid
    
    async def delete_category(self,category_id):
        cursor = await self.conn.execute(
                    "DELETE FROM categories WHERE category_id = ?",(category_id,),)
        await self.conn.commit()
        return cursor.lastrowid
    
    async def set_timezone(self,user_id, zone):
        cursor = await self.conn.execute(
                    "UPDATE users SET timezone = ? WHERE user_id = ?",(zone,user_id,),)
        await self.conn.commit()
        return cursor.lastrowid

    async def set_nickname(self,user_id, nickname):
        cursor = await self.conn.execute(
                    "UPDATE users SET nickname = ? WHERE user_id = ?",(nickname,user_id,),)
        await self.conn.commit()
        return cursor.lastrowid

    async def list_recent_transactions(self, budget_id, limit, offset, kind=None):
        query = """SELECT e.expense_id, e.date, e.amount, e.kind, e.added_by,
                          COALESCE(c.name, 'Без категории') AS category_name,
                          COALESCE(u.nickname, '') AS nickname
                   FROM expenses e
                   LEFT JOIN categories c ON c.category_id = e.category_id
                   LEFT JOIN users u ON u.user_id = e.added_by
                   WHERE e.budget_id = ?"""
        params = [budget_id]
        if kind is not None:
            query += " AND e.kind = ?"
            params.append(kind)
        query += " ORDER BY e.expense_id DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        async with self.conn.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def count_transactions(self, budget_id, kind=None):
        query = "SELECT COUNT(*) AS c FROM expenses WHERE budget_id = ?"
        params = [budget_id]
        if kind is not None:
            query += " AND kind = ?"
            params.append(kind)
        async with self.conn.execute(query, params) as cursor:
            row = await cursor.fetchone()
        return row["c"] if row else 0


import shutil
from pathlib import Path
from datetime import datetime

async def backup_db(db: Database, backup_dir: Path, keep: int = 14):
    backup_dir.mkdir(parents=True, exist_ok=True)
    name = f"expenses-{datetime.now():%Y-%m-%d_%H%M}.db"
    dest = backup_dir / name

    # безопасная копия через SQLite API, а не shutil.copy —
    # копирование "на лету" может захватить базу в неконсистентном состоянии
    backup_conn = await aiosqlite.connect(dest)
    await db.conn.backup(backup_conn)
    await backup_conn.close()

    # ротация: оставляем только последние `keep` файлов
    files = sorted(backup_dir.glob("expenses-*.db"), reverse=True)
    for old in files[keep:]:
        old.unlink()

    return dest

async def backup_loop(db: Database, backup_dir: Path):
    while True:
        try:
            path = await backup_db(db, backup_dir)
            logger.info("бэкап создан: %s", path)
        except Exception:
            logger.exception("сбой при создании бэкапа")
        await asyncio.sleep(24 * 60 * 60)      # раз в сутки
"""Быстрая проверка логики без Telegram. Запуск: python smoke_test.py"""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from db import Database
from utils import parse_amount, format_money


def test_utils() -> None:
    assert parse_amount("250") == 25000
    assert parse_amount("5,5") == 550
    assert parse_amount("5,50") == 550
    assert parse_amount("12,05") == 1205
    assert parse_amount("абв") is None
    assert parse_amount("") is None
    assert parse_amount("1.2.3") is None
    assert format_money(25000) == "250"
    print("utils ✓")


async def test_db() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        await db.connect()

        # --- пользователь и бюджет ---
        user = await db.ensure_user(111)
        assert user["current_budget"] is None
        assert (await db.ensure_user(111))["current_budget"] is None  # идемпотентность

        budget_id = await db.create_budget(111)
        user = await db.ensure_user(111)
        assert user["current_budget"] == budget_id

        # --- дефолтные категории приехали с разделением по kind ---
        expense_cats = await db.list_active_categories(budget_id, "expense")
        income_cats = await db.list_active_categories(budget_id, "income")
        assert len(expense_cats) == 9, len(expense_cats)
        assert len(income_cats) == 4, len(income_cats)
        assert expense_cats[0]["name"] == "Продукты"        # sort_order соблюдён
        food_id = expense_cats[0]["category_id"]
        salary_id = income_cats[0]["category_id"]

        # --- расходы за два месяца ---
        await db.add_expense(budget_id, 111, food_id, 25000, "2026-07-05", "expense")
        await db.add_expense(budget_id, 111, food_id, 10000, "2026-07-20", "expense")
        await db.add_expense(budget_id, 111, expense_cats[2]["category_id"], 5000, "2026-08-01", "expense")

        assert await db.stats_total(budget_id, "2026-07-01", "2026-07-31", "expense") == 35000
        assert await db.stats_total(budget_id, "2026-09-01", "2026-09-30", "expense") == 0

        stats = await db.expense_by_category(budget_id, "2026-07-01", "2026-07-31")
        assert sum(r["total"] for r in stats) == 35000  # разбивка сходится с общей

        # --- доход отдельно от расхода ---
        await db.add_expense(budget_id, 111, salary_id, 500000, "2026-07-01", "income")
        assert await db.stats_total(budget_id, "2026-07-01", "2026-07-31", "expense") == 35000  # не смешались
        assert await db.stats_total(budget_id, "2026-07-01", "2026-07-31", "income") == 500000

        income_stats = await db.income_by_category(budget_id, "2026-07-01", "2026-07-31")
        assert sum(r["total"] for r in income_stats) == 500000
        # расходная категория не протекла в доходный отчёт
        assert all(r["name"] != "Продукты" for r in income_stats)

        # --- kind не путается при создании / переименовании / поиске дублей ---
        max_order = await db.get_maximum_sort_order(budget_id, "expense")
        new_id = await db.add_category("Такси", budget_id, 0, max_order + 10, "expense")
        assert await db.check_category_name(budget_id, "Такси", "expense") is not None
        assert await db.check_category_name(budget_id, "Такси", "income") is None  # разные kind не пересекаются

        # --- архивация не рвёт историю ---
        await db.archive_category(food_id)
        active = await db.list_active_categories(budget_id, "expense")
        assert food_id not in [c["category_id"] for c in active]
        stats_after_archive = await db.expense_by_category(budget_id, "2026-07-01", "2026-07-31")
        assert any(r["name"] == "Продукты" for r in stats_after_archive)  # но в отчёте всё ещё видна

        await db.dearchive_category(food_id)
        active = await db.list_active_categories(budget_id, "expense")
        assert food_id in [c["category_id"] for c in active]

        # --- второй участник в тот же бюджет ---
        await db.ensure_user(222)
        await db.add_to_budget(222, budget_id)
        user2 = await db.ensure_user(222)
        assert user2["current_budget"] == budget_id

        # --- часовой пояс ---
        await db.set_timezone(111, "Europe/Rome")
        user = await db.ensure_user(111)
        assert user["timezone"] == "Europe/Rome"

        # --- приглашение в бюджет по коду ---
        code = await db.get_invite_code(budget_id)
        assert code is not None
        assert await db.check_invite_code(code) == budget_id
        assert await db.check_invite_code("не-существует") is None

        await db.close()
        print("db ✓")


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


if __name__ == "__main__":
    test_utils()
    asyncio.run(test_db())
    asyncio.run(test_migrations_idempotent())
    print("Все проверки пройдены")
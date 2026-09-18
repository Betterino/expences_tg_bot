"""Hardcoded datasets, deliberately hostile.

Rows are plain dicts on purpose: aiosqlite.Row is also an index-by-name mapping, so a
renderer cannot tell a fixture from a real DB row. Amounts are kopeks, like the DB.
"""
from sandbox import TableData

DEMO_EXPENSE = [
    {"name": "Продукты", "total": 1234000, "maximum": 1500000},          # обычная строка
    {"name": "Кафе &amp; бары", "total": 87650, "maximum": 50000},        # экранированный &, перерасход
    {"name": "Жилье и ЖКУ 15", "total": 12345678, "maximum": 0},         # длинное имя, без максимума
    {"name": "Связь", "total": 1205, "maximum": 200000},                 # копейки -> «12,05»
    {"name": "Развлечения", "total": 0, "maximum": 300000},              # нулевые траты
    {"name": "Прочее", "total": 50000, "maximum": 50000},                # ровно 100%
]

DEMO_INCOME = [
    {"name": "Зарплата", "total": 15000000, "maximum": 0},
    {"name": "Подарки &lt;3", "total": 250000, "maximum": 0},
]

DEMO = TableData(
    start="2026-03-01",
    end="2026-03-31",
    total_e=sum(r["total"] for r in DEMO_EXPENSE),
    expense=DEMO_EXPENSE,
    income=DEMO_INCOME,
    total_i=sum(r["total"] for r in DEMO_INCOME),
)

# Новый бюджет, первое число месяца: ни одной записи.
EMPTY = TableData("2026-03-01", "2026-03-31", 0, [], [], 0)

# 40 категорий: проверка лимита в 4096 символов.
_LONG_EXPENSE = [
    {"name": f"Категория {i:02d}", "total": i * 11111, "maximum": i * 20000}
    for i in range(1, 41)
]
LONG = TableData(
    start="2026-01-01",
    end="2026-12-31",
    total_e=sum(r["total"] for r in _LONG_EXPENSE),
    expense=_LONG_EXPENSE,
    income=DEMO_INCOME,
    total_i=sum(r["total"] for r in DEMO_INCOME),
)

FIXTURES = {"demo": DEMO, "empty": EMPTY, "long": LONG}

"""Bulk import of transactions from a JSON file the user's own AI assembled.

Pure `data -> data` like ui/views.py: no aiogram, no DB. handlers/importer.py feeds it the
file bytes plus this budget's active categories and gets back either rows ready for
Database.create_import or a list of human-readable errors -- never both.

The schema handed out (build_schema) embeds the budget's exact category names as an
`enum`, so the AI picks from a closed list; anything else is rejected rather than guessed.
Everything in the file is untrusted input: category names that fail to match get echoed
back in error messages, so the handler must html.escape them (parse_mode is HTML).
"""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, timedelta

from expenses_bot.constants import KINDS
from expenses_bot.utils import parse_term, visible

FORMAT_VERSION = 1
MAX_FILE_BYTES = 256 * 1024
MAX_ROWS = 1000
MAX_AGE_DAYS = 366
MAX_ERRORS_SHOWN = 10


@dataclass(frozen=True)
class ImportRow:
    date: str          # ISO YYYY-MM-DD
    kind: str          # expense | income
    category_id: int
    amount: int        # kopeks, > 0


@dataclass
class ImportResult:
    rows: list[ImportRow] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _key(name: str) -> str:
    """How a file's category name is matched to a stored one: what the user sees
    (stored names are html-escaped, utils.visible), case- and edge-space-insensitive."""
    return visible(name).strip().casefold()


def build_schema(categories_by_kind: dict[str, list[str]], today: date) -> dict:
    """JSON Schema of the import file. `categories_by_kind` holds *visible* names."""
    def tx(kind: str) -> dict:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["date", "kind", "category", "amount"],
            "properties": {
                "date": {"type": "string", "format": "date",
                         "description": f"YYYY-MM-DD, не позже {today.isoformat()}"},
                "kind": {"const": kind},
                "category": {"enum": categories_by_kind.get(kind, [])},
                "amount": {"type": "string", "pattern": r"^\d+([.,]\d{1,2})?$",
                           "description": "Положительная сумма, до 2 знаков после запятой"},
            },
        }

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Импорт трат и доходов",
        "type": "object",
        "additionalProperties": False,
        "required": ["version", "transactions"],
        "properties": {
            "version": {"const": FORMAT_VERSION},
            "transactions": {
                "type": "array",
                "minItems": 1,
                "maxItems": MAX_ROWS,
                "items": {"oneOf": [tx(k) for k in KINDS]},
            },
        },
    }


def example(categories_by_kind: dict[str, list[str]], today: date) -> dict:
    expense = (categories_by_kind.get("expense") or ["Продукты"])[0]
    transactions = [{"date": today.isoformat(), "kind": "expense", "category": expense, "amount": "123.45"}]
    if categories_by_kind.get("income"):
        transactions.append({"date": today.isoformat(), "kind": "income",
                             "category": categories_by_kind["income"][0], "amount": "5000"})
    return {"version": FORMAT_VERSION, "transactions": transactions}


def ai_prompt(today: date) -> str:
    """Instructions for the user's AI. Plain text -- the handler escapes it for HTML."""
    return (
        "Составь JSON-файл с моими тратами и доходами строго по приложенной JSON-схеме "
        "(schema.json). Данные — ниже/на фото.\n"
        "Правила:\n"
        "• category — только одно из значений enum в схеме, ничего не придумывай; "
        "если не уверен, бери самую близкую по смыслу.\n"
        "• kind: \"expense\" — трата, \"income\" — доход.\n"
        f"• date — в формате ГГГГ-ММ-ДД; сегодня {today.isoformat()}. Если год не указан — "
        "ближайшая прошедшая дата.\n"
        "• amount — строкой, положительное число, до 2 знаков после точки, без валюты.\n"
        "• Несколько позиций одного чека в одной категории можно сложить в одну запись.\n"
        "• Ответь только файлом import.json, без пояснений."
    )


def _parse_amount(value) -> int | None:
    # bool is an int subclass: true/false must not sneak in as 1/0 rubles.
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    amount = parse_term(str(value).strip())
    return amount if amount is not None and amount > 0 else None


def parse_import(raw: bytes, categories: dict[str, dict[str, int]], today: date) -> ImportResult:
    """`categories`: kind -> {stored category name -> category_id} (active categories only).

    All-or-nothing: a single bad row means no rows are returned, so the user fixes the
    file and resends it instead of ending up with half an import."""
    result = ImportResult()
    try:
        data = json.loads(raw.decode("utf-8-sig"))  # -sig: tolerate a BOM from Windows editors
    except (UnicodeDecodeError, json.JSONDecodeError):
        result.errors.append("файл не похож на JSON")
        return result
    if not isinstance(data, dict) or not isinstance(data.get("transactions"), list):
        result.errors.append('нет списка "transactions" на верхнем уровне')
        return result
    if data.get("version", FORMAT_VERSION) != FORMAT_VERSION:
        result.errors.append(f"неизвестная версия формата: {data.get('version')!r}")
        return result
    items = data["transactions"]
    if not items:
        result.errors.append("список transactions пуст")
        return result
    if len(items) > MAX_ROWS:
        result.errors.append(f"слишком много записей: {len(items)}, максимум {MAX_ROWS}")
        return result

    lookup = {kind: {_key(name): cid for name, cid in by_name.items()}
              for kind, by_name in categories.items()}
    oldest = today - timedelta(days=MAX_AGE_DAYS)
    rows = []
    for n, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            result.errors.append(f"запись {n}: не объект")
            continue
        kind = item.get("kind")
        if kind not in KINDS:
            result.errors.append(f"запись {n}: kind должен быть expense или income")
            continue
        try:
            when = date.fromisoformat(str(item.get("date", "")))
        except ValueError:
            result.errors.append(f"запись {n}: дата не в формате ГГГГ-ММ-ДД")
            continue
        if when > today:
            result.errors.append(f"запись {n}: дата {when.isoformat()} в будущем")
            continue
        if when < oldest:
            result.errors.append(f"запись {n}: дата {when.isoformat()} старше года")
            continue
        name = item.get("category")
        category_id = lookup.get(kind, {}).get(_key(name)) if isinstance(name, str) else None
        if category_id is None:
            result.errors.append(f"запись {n}: нет категории {str(name)[:40]!r}")
            continue
        amount = _parse_amount(item.get("amount"))
        if amount is None:
            result.errors.append(f"запись {n}: непонятная сумма {str(item.get('amount'))[:20]!r}")
            continue
        rows.append(ImportRow(when.isoformat(), kind, category_id, amount))

    if not result.errors:
        result.rows = rows
    return result


def digest(rows: list[ImportRow]) -> str:
    """Fingerprint of the *content*, order-independent: a re-sent file -- reformatted,
    reordered, with different whitespace -- still counts as the same import."""
    canon = sorted((r.date, r.kind, r.category_id, r.amount) for r in rows)
    return hashlib.sha256(json.dumps(canon).encode()).hexdigest()


def summary(rows: list[ImportRow]) -> dict:
    totals = {kind: sum(r.amount for r in rows if r.kind == kind) for kind in KINDS}
    counts = {kind: sum(1 for r in rows if r.kind == kind) for kind in KINDS}
    dates = [r.date for r in rows]
    return {"count": len(rows), "first": min(dates), "last": max(dates), "totals": totals, "counts": counts}

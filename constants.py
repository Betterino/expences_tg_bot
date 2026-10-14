from dotenv import get_key

from texts import Buttons

VERSION = "1.6.0"
CHANGELOG_URL = ""  # заполняется вручную ссылкой на хостинг CHANGELOG.md

# Gates the 🧪 Тест sandbox button/router (SEC-8) -- a development tool that exposes
# internals (variant keys, character budgets), not meant for every user in production.
_admin_id_raw = get_key(".env", "ADMIN_ID")
ADMIN_ID = int(_admin_id_raw) if _admin_id_raw else None

PER_PAGE = 6

# Domains of the free-string CallbackData fields `kind` and `mode` (validators.py).
KINDS = ("expense", "income")
ADD_MODES = ("today", "yesterday", "date")

# History screen toggle cycles: keyed on the field's current value, mapping to
# (next value, label for the *current* value). history_kb() and tests/test_history_filters.py
# read this same table, so the button labels and the cycle order live in one place.
HISTORY_CYCLES = {
    "who": {
        "all": ("mine", Buttons.HISTORY_WHO_ALL),
        "mine": ("all", Buttons.HISTORY_WHO_MINE),
    },
    "kind": {
        None: ("expense", Buttons.HISTORY_KIND_ALL),
        "expense": ("income", Buttons.HISTORY_KIND_EXPENSE),
        "income": (None, Buttons.HISTORY_KIND_INCOME),
    },
    "sort": {
        "id": ("date", Buttons.HISTORY_SORT_BY_ID),
        "date": ("id", Buttons.HISTORY_SORT_BY_DATE),
    },
}
EDIT_PURPOSE = {"edit_max": "changemax", "edit_name": "changename",
                "edit_delete": "delete", "archive": "archive", "dearchive": "dearchive"}
TIMEZONES = [
    ("Кишинёв", "Europe/Chisinau"),
    ("Москва", "Europe/Moscow"),
    ("Киев", "Europe/Kyiv"),
    ("Минск", "Europe/Minsk"),
    ("Варшава", "Europe/Warsaw"),
    ("Берлин", "Europe/Berlin"),
    ("Лондон", "Europe/London"),
    ("Тбилиси", "Asia/Tbilisi"),
    ("Ереван", "Asia/Yerevan"),
    ("Алматы", "Asia/Almaty"),
    ("Екатеринбург", "Asia/Yekaterinburg"),
    ("Новосибирск", "Asia/Novosibirsk"),
]

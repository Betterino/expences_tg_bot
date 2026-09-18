"""Strings for the sandbox screen only.

Deliberately NOT in the project's texts.py: everything throwaway stays inside this
package so removing the sandbox is a directory deletion plus three reverted lines.
"""


class Sandbox:
    TITLE = "🧪 Песочница таблиц"
    HEADER = "🧪 <b>{label}</b> · {source} · {size}/4096\n"
    COPY = "📤 Отправить копией"
    COPIED = "Отправил копией — сравнивай в ленте"
    SOURCE_BUTTON = "🗃 Данные: {source} ▸"
    SOURCE_LABELS = {
        "demo": "образец",
        "empty": "пусто",
        "long": "40 категорий",
        "live": "мои данные",
    }
    NO_BUDGET = "Бюджета нет — показываю образец"
    TOO_LONG = "Не влезло в 4096 символов — вариант обрезан"
    RICH_HEADER = "🧪 {label} · {source} · {size}/32768"
    RICH_UNAVAILABLE = "Rich-сообщения недоступны — показываю «Как сейчас»"

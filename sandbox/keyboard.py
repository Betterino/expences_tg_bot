from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from callback import NavCB
from sandbox.callback import SandboxCB
from sandbox.texts import Sandbox as SandboxTexts
from sandbox.variants import VARIANTS
from texts import Buttons

# Порядок перебора кнопкой «Данные»: образец -> пусто -> 40 категорий -> мои -> образец
SOURCES = ("demo", "empty", "long", "live")


def next_source(source: str) -> str:
    return SOURCES[(SOURCES.index(source) + 1) % len(SOURCES)] if source in SOURCES else SOURCES[0]


def sandbox_kb(current: str, source: str):
    """Built entirely from the registry -- adding a variant needs no edit here."""
    builder = InlineKeyboardBuilder()
    for v in VARIANTS:
        mark = "✅ " if v.key == current else ""
        data = SandboxCB(action="show", key=v.key, source=source)
        builder.button(text=f"{mark}{v.label}", callback_data=data)
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(
            text=SandboxTexts.COPY,
            callback_data=SandboxCB(action="copy", key=current, source=source).pack(),
        ),
        InlineKeyboardButton(
            text=SandboxTexts.SOURCE_BUTTON.format(source=SandboxTexts.SOURCE_LABELS[source]),
            callback_data=SandboxCB(action="show", key=current, source=next_source(source)).pack(),
        ),
    )
    builder.row(InlineKeyboardButton(text=Buttons.BACK, callback_data=NavCB(to="set").pack()))
    return builder.as_markup()

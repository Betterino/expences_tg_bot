"""Property tests for the table-rendering sandbox.

Every table test loops over VARIANTS x FIXTURES, so adding or deleting a rendering
style never requires editing this file -- which is the point, since the whole sandbox
exists to be iterated on.
"""
from html.parser import HTMLParser

import handlers
from callback import NavCB
from keyboards import settings_kb
from sandbox.callback import SandboxCB
from sandbox.fixtures import FIXTURES
from sandbox.handlers import MESSAGE_LIMIT, send_copy, show_variant
from sandbox.handlers import router as sandbox_router
from sandbox.keyboard import SOURCES, next_source, sandbox_kb
from sandbox.variants import VARIANTS, get, render
from tests.fakes import FakeCallbackQuery, find_button, unpack_callback_data
from texts import Buttons

# Подмножество HTML, которое понимает Telegram.
ALLOWED_TAGS = {"b", "i", "u", "s", "code", "pre", "blockquote", "tg-spoiler", "a"}
ALLOWED_ENTITIES = {"amp", "lt", "gt", "quot"}


class _Html(HTMLParser):
    """Telegram's HTML subset has no void tags, so a plain stack is a valid balance check."""

    def __init__(self):
        super().__init__(convert_charrefs=False)  # оставляем &amp; отдельным событием
        self.stack: list[str] = []
        self.data: list[str] = []

    def handle_starttag(self, tag, attrs):
        assert tag in ALLOWED_TAGS, f"Telegram не знает тег <{tag}>"
        self.stack.append(tag)

    def handle_endtag(self, tag):
        assert self.stack and self.stack[-1] == tag, f"незакрытый тег: {tag} при стеке {self.stack}"
        self.stack.pop()

    def handle_data(self, data):
        self.data.append(data)

    def handle_entityref(self, name):
        assert name in ALLOWED_ENTITIES, f"неизвестная сущность &{name};"


def _parse(text: str) -> _Html:
    parser = _Html()
    parser.feed(text)
    parser.close()
    return parser


def _all_renders():
    for v in VARIANTS:
        for fixture_name, data in FIXTURES.items():
            yield v, fixture_name, render(v.key, data)


def test_every_variant_renders_every_fixture() -> None:
    for v, fixture_name, body in _all_renders():
        assert isinstance(body, str) and body.strip(), f"{v.key} на {fixture_name} вернул пустоту"


def test_every_variant_emits_valid_html() -> None:
    for v, fixture_name, body in _all_renders():
        parser = _parse(body)
        assert not parser.stack, f"{v.key} на {fixture_name}: не закрыты {parser.stack}"


def test_every_variant_escapes_its_data() -> None:
    for v, fixture_name, body in _all_renders():
        text = "".join(_parse(body).data)
        assert "<" not in text, f"{v.key} на {fixture_name}: неэкранированный < в данных"
        assert "&" not in text, f"{v.key} на {fixture_name}: голый & вместо сущности"


def test_every_variant_fits_message_limit() -> None:
    for v, fixture_name, body in _all_renders():
        assert len(body) < MESSAGE_LIMIT, f"{v.key} на {fixture_name}: {len(body)} символов"


def test_variant_keys_are_unique_and_packable() -> None:
    keys = [v.key for v in VARIANTS]
    assert len(keys) == len(set(keys))
    for key in keys:
        packed = SandboxCB(action="show", key=key, source="live").pack()
        assert len(packed.encode()) <= 64, f"{key}: callback data {len(packed.encode())} байт"


def test_unknown_variant_key_falls_back_instead_of_raising() -> None:
    assert get("выпилен-20-минут-назад") is VARIANTS[0]


def test_sandbox_kb_has_a_button_per_variant() -> None:
    markup = sandbox_kb(VARIANTS[0].key, "demo")
    buttons = [b for row in markup.inline_keyboard for b in row]
    assert len(buttons) == len(VARIANTS) + 3  # + копия, источник, назад
    for v in VARIANTS:
        assert find_button(markup, v.label) is not None, f"нет кнопки для {v.key}"


def test_sandbox_kb_marks_only_the_current_variant() -> None:
    markup = sandbox_kb(VARIANTS[2].key, "demo")
    marked = [b.text for row in markup.inline_keyboard for b in row if b.text.startswith("✅")]
    assert len(marked) == 1 and VARIANTS[2].label in marked[0]


def test_sandbox_back_button_returns_to_settings() -> None:
    markup = sandbox_kb(VARIANTS[0].key, "demo")
    assert unpack_callback_data(markup, -1, 0, NavCB).to == "set"


def test_source_button_cycles_through_every_source() -> None:
    seen = [SOURCES[0]]
    for _ in range(len(SOURCES)):
        seen.append(next_source(seen[-1]))
    assert set(seen) == set(SOURCES) and seen[0] == seen[-1]


def test_settings_menu_offers_the_sandbox() -> None:
    button = find_button(settings_kb(), Buttons.SANDBOX)
    assert button is not None and NavCB.unpack(button.callback_data).to == "sandbox"


def test_sandbox_router_precedes_edit_router() -> None:
    order = list(handlers.routers)
    assert order.index(sandbox_router) < order.index(handlers.edit.router)


async def test_fixture_source_never_touches_the_db() -> None:
    # db=None доказывает это: любое обращение к базе упало бы с AttributeError.
    callback = FakeCallbackQuery()
    data = SandboxCB(action="show", key="grid", source="demo")
    await show_variant(callback, callback_data=data, db=None, budget_id=None, tz="Europe/Moscow")
    callback.message.edit_text.assert_awaited_once()
    callback.answer.assert_awaited_once()
    assert "Рамки" in callback.message.edit_text.await_args.kwargs["text"]


async def test_copy_sends_a_new_message_instead_of_editing() -> None:
    callback = FakeCallbackQuery()
    data = SandboxCB(action="copy", key="narrow", source="demo")
    await send_copy(callback, callback_data=data, db=None, budget_id=None, tz="Europe/Moscow")
    callback.message.answer.assert_awaited_once()
    callback.message.edit_text.assert_not_awaited()
    callback.answer.assert_awaited_once()
    print(f"sandbox: {len(VARIANTS)} вариантов x {len(FIXTURES)} наборов ✓")


async def test_sandbox_button_is_not_swallowed_by_edits_catch_all() -> None:
    """Same technique as tests/test_routing.py: push a real event through the actual
    Dispatcher chain. Calling handlers directly cannot catch an earlier router's
    catch-all shadowing them; only a full-stack dispatch can."""
    import tempfile
    import traceback
    from pathlib import Path

    from aiogram import Dispatcher
    from aiogram.types import CallbackQuery, Chat, Message, User

    from db import Database
    from handlers import routers

    class _FakeState:
        async def get_state(self):
            return None

        async def get_data(self):
            return {}

    user = User(id=222, is_bot=False, first_name="t")
    message = Message(message_id=1, date=0, chat=Chat(id=1, type="private"))
    callback = CallbackQuery(
        id="1", from_user=user, chat_instance="x", data="nav:sandbox:expense", message=message
    )

    with tempfile.TemporaryDirectory() as tmp:
        async with Database(Path(tmp) / "test.db") as db:
            await db.ensure_user(222)
            budget_id = await db.create_budget(222)
            # Router.parent_router is a one-time assignment -- aiogram refuses to
            # attach the same Router to a second Dispatcher. tests/test_routing.py
            # runs first (alphabetically) and already claimed handlers.routers, so
            # reuse whatever they are mounted on instead of building a rival chain.
            root = sandbox_router
            while root.parent_router is not None:
                root = root.parent_router
            if isinstance(root, Dispatcher):
                dp = root
            else:
                dp = Dispatcher()
                for r in routers:
                    dp.include_router(r)
            try:
                await dp.propagate_event(
                    "callback_query",
                    callback,
                    db=db,
                    budget_id=budget_id,
                    tz="Europe/Moscow",
                    state=_FakeState(),
                    user={"user_id": 222},
                )
            except RuntimeError as error:
                # edit_text() without a live Bot always fails; the traceback's origin is
                # what proves which handler actually ran.
                assert "mount" in str(error), error
                assert "sandbox/handlers.py" in traceback.format_exc(), traceback.format_exc()
            else:
                raise AssertionError("ожидали RuntimeError от edit_text без живого Bot")

"""Menu help (collapsible) and the About screen.

The parity test is the point of the whole design: MENU_HELP is keyed on Buttons.*,
so adding a button to main_menu() without a matching help line fails loudly here
instead of silently shipping an unexplained button.
"""
import richtext
from callback import NavCB
from constants import VERSION
from handlers.common import about_screen, cancel, handle_start, main_menu_handler
from keyboards import main_menu
from tests.fakes import FakeCallbackQuery, FakeMessage, make_state, rich_blocks
from texts import Screens
from views import menu_view


def _button_texts(markup) -> set[str]:
    return {btn.text for row in markup.inline_keyboard for btn in row}


def test_menu_view_has_title_and_details_covering_every_button_label() -> None:
    blocks = menu_view()
    assert isinstance(blocks[0], type(richtext.para("")))
    details = blocks[1]
    assert getattr(details, "summary", None) == Screens.MENU_HELP_SUMMARY

    text = "".join(richtext.walk_text(blocks))
    for label in _button_texts(main_menu()):
        assert label in text, f"{label!r} missing from menu help"


def test_menu_help_parity_with_main_menu_buttons() -> None:
    assert _button_texts(main_menu()) == {label for label, _desc in Screens.MENU_HELP}


async def test_main_menu_handler_renders_rich_menu() -> None:
    state = make_state()
    callback = FakeCallbackQuery()
    await main_menu_handler(callback, state)
    callback.message.edit_text.assert_awaited_once()
    kwargs = callback.message.edit_text.await_args.kwargs
    assert "rich_message" in kwargs
    assert "text" not in kwargs


async def test_handle_start_with_budget_uses_answer_rich() -> None:
    message = FakeMessage()
    await handle_start(message, budget_id=1)
    message.answer_rich.assert_awaited_once()


async def test_cancel_shows_menu_after_clearing_state() -> None:
    state = make_state()
    await state.update_data(kind="expense")
    message = FakeMessage()
    await cancel(message, state)
    message.answer_rich.assert_awaited_once()
    assert await state.get_data() == {}


async def test_about_reachable_from_menu_and_shows_version() -> None:
    about_targets = [
        NavCB.unpack(btn.callback_data)
        for row in main_menu().inline_keyboard
        for btn in row
        if btn.callback_data.startswith("nav:")
    ]
    assert NavCB(to="about") in about_targets

    callback = FakeCallbackQuery()
    await about_screen(callback)
    blocks = rich_blocks(callback.message.edit_text)
    text = "".join(richtext.walk_text(blocks))
    assert VERSION in text

    markup = callback.message.edit_text.await_args.kwargs["reply_markup"]
    assert any(
        NavCB.unpack(btn.callback_data) == NavCB(to="menu")
        for row in markup.inline_keyboard
        for btn in row
    )

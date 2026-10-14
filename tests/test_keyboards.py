"""Row-count regression guard for the keyboard layouts compacted via .adjust().
Catches silent layout regressions (e.g. someone reverting .adjust(2) to .adjust(1))
without needing a live bot to render anything."""
from callback import HistoryPageCB, NavCB
from keyboards import confirm, edit_archived_kb, edit_kb, history_kb, main_menu, settings_kb
from tests.fakes import unpack_callback_data


def test_main_menu_is_five_rows() -> None:
    # 9 buttons (8 + "О боте"), .adjust(2) -> 2,2,2,2,1
    assert len(main_menu().inline_keyboard) == 5


def test_edit_kb_expense_is_three_rows() -> None:
    assert len(edit_kb("expense").inline_keyboard) == 3


def test_edit_kb_income_is_three_rows() -> None:
    assert len(edit_kb("income").inline_keyboard) == 3


def test_confirm_is_one_row() -> None:
    assert len(confirm("yes", "no").inline_keyboard) == 1


def test_edit_archived_kb_is_one_row() -> None:
    assert len(edit_archived_kb().inline_keyboard) == 1


def test_settings_kb_is_two_rows() -> None:
    assert len(settings_kb().inline_keyboard) == 2


def test_history_kb_shape() -> None:
    # toggle row, no pagination (single page), menu row
    markup = history_kb(page=1, max_page=1)
    assert len(markup.inline_keyboard) == 2
    assert len(markup.inline_keyboard[0]) == 3  # who/kind/sort toggles

    # toggle row, pagination row, menu row
    markup = history_kb(page=2, max_page=3)
    assert len(markup.inline_keyboard) == 3

    # toggles carry the NEXT value, not the current one
    who_cb = unpack_callback_data(markup, 0, 0, HistoryPageCB)
    assert who_cb.who == "mine"
    assert who_cb.page == 1  # changing a filter always resets to page 1
    kind_cb = unpack_callback_data(markup, 0, 1, HistoryPageCB)
    assert kind_cb.kind == "expense"
    sort_cb = unpack_callback_data(markup, 0, 2, HistoryPageCB)
    assert sort_cb.sort == "date"

    menu_cb = unpack_callback_data(markup, 2, 0, NavCB)
    assert menu_cb == NavCB(to="menu")

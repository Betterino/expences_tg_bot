"""Row-count regression guard for the keyboard layouts compacted via .adjust().
Catches silent layout regressions (e.g. someone reverting .adjust(2) to .adjust(1))
without needing a live bot to render anything."""
from keyboards import main_menu, edit_kb, confirm, edit_archived_kb, settings_kb


def test_main_menu_is_four_rows() -> None:
    assert len(main_menu().inline_keyboard) == 4
    print("keyboards: main_menu ✓")


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
    print("keyboards ✓")

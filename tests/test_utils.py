from utils import format_money, parse_amount


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

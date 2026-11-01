from aiogram.filters.callback_data import CallbackData


class OnboardCB(CallbackData, prefix="onb"):
    action: str          # create | join

class AddCB(CallbackData,prefix="add"):
    mode: str
    kind: str = "expense"

class CategoryCB(CallbackData, prefix="cat"):
    id: int
    purpose: str
    kind: str = "expense"
    mode: str = "today"  # today | yesterday | date -- carried from AddCB so the add-expense
                          # flow doesn't depend on FSM state surviving a concurrent nav tap

class CatPageCB(CallbackData,prefix="page"):
    page: int
    purpose: str
    kind: str = "expense"
    mode: str = "today"

class MonthCB(CallbackData,prefix="mon"):
    purpose: str # single | from | to
    month: int

class StatsCB(CallbackData, prefix="st"):
    year: int
    month: int

class RangeCB(CallbackData,prefix="ran"):
    year_month: str

class TzCB(CallbackData, prefix="tz"):
    index: int | None = None      # None = ручной ввод


class NavCB(CallbackData,prefix="nav"):
    to: str  # menu | stats | edit | add | range | code
            # edit_
    kind: str = "expense"
    mode: str = "today"  # only meaningful for to="add_again" -- see CategoryCB.mode

class HistoryPageCB(CallbackData, prefix="hpg"):
    page: int
    kind: str | None = None  # None = комбинированная лента | "expense" | "income"
    who: str = "all"         # all | mine
    sort: str = "id"         # id = по добавлению | date = по дате операции

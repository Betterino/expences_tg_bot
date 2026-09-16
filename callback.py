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

class CatPageCB(CallbackData,prefix="page"):
    page: int
    purpose: str
    kind: str = "expense"

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

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from callback import (
    AddCB,
    CategoryCB,
    CatPageCB,
    HistoryPageCB,
    MonthCB,
    NavCB,
    OnboardCB,
    RangeCB,
    StatsCB,
    TzCB,
)
from constants import HISTORY_CYCLES, TIMEZONES
from texts import MONTHS, Buttons
from utils import shift_month


def choose_range_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.BY_YEAR, callback_data=RangeCB(year_month="year"))
    builder.button(text=Buttons.BY_MONTH, callback_data=RangeCB(year_month="month"))
    builder.button(text=Buttons.BY_MONTHS, callback_data=RangeCB(year_month="months"))
    builder.button(text=Buttons.CANCEL,callback_data=NavCB(to="stats"))
    builder.adjust(1)
    return builder.as_markup()

def edit_kb(kind = "expense"):
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.ADD_CATEGORY,callback_data=NavCB(to="edit_cat",kind=kind))
    if kind == "expense":
        builder.button(text=Buttons.EDIT_MAXIMUM,callback_data=NavCB(to="edit_max",kind=kind))
    builder.button(text=Buttons.EDIT_NAME,callback_data=NavCB(to="edit_name",kind=kind))
    builder.button(text=Buttons.ARCHIVE_CATEGORY,callback_data=NavCB(to="edit_arch",kind=kind))
    builder.button(text=Buttons.DELETE_CATEGORY,callback_data=NavCB(to="edit_delete",kind=kind))
    #builder.button(text="Последовательность категорий")
    builder.button(text=Buttons.MENU,callback_data=NavCB(to="menu"))
    builder.adjust(2)
    return builder.as_markup()


def date_expense_kb(kind):
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.TODAY,callback_data=AddCB(mode="today",kind=kind))
    builder.button(text=Buttons.YESTERDAY,callback_data=AddCB(mode="yesterday",kind=kind))
    builder.button(text=Buttons.INPUT_DATE,callback_data=AddCB(mode="date",kind=kind))
    builder.button(text=Buttons.MENU,callback_data=NavCB(to="menu"))
    builder.adjust(1)
    return builder.as_markup()

def stats_kb(year,month):
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.CHOOSE_OTHER_PERIOD,callback_data=NavCB(to="stats_choose"))
    builder.button(text=Buttons.MENU,callback_data=NavCB(to="menu"))
    builder.adjust(1)
    prev_year, prev_month = shift_month(year,month,-1)
    next_year, next_month = shift_month(year,month,1)
    prev_btn = InlineKeyboardButton(
        text=Buttons.PREV_PAGE, callback_data=StatsCB(year=prev_year, month=prev_month).pack()
    )
    next_btn = InlineKeyboardButton(
        text=Buttons.NEXT_PAGE, callback_data=StatsCB(year=next_year, month=next_month).pack()
    )
    builder.row(prev_btn,next_btn)
    return builder.as_markup()

def special_stats_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.CHOOSE_OTHER_PERIOD,callback_data=NavCB(to="stats_choose"))
    builder.button(text=Buttons.MENU,callback_data=NavCB(to="menu"))
    return builder.as_markup()

def onboarding_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.CREATE_BUDGET, callback_data=OnboardCB(action="create"))
    builder.button(text=Buttons.JOIN_BUDGET, callback_data=OnboardCB(action="join"))
    builder.adjust(1)
    return builder.as_markup()

def months_kb(purpose:str,start = 0):
    builder = InlineKeyboardBuilder()
    for i in range(start,11):
        builder.button(text=MONTHS[i], callback_data=MonthCB(month=i,purpose=purpose))
    if purpose != "from":
        builder.button(text=MONTHS[11],callback_data=MonthCB(month=11,purpose=purpose))
        builder.adjust((12-start)//2,(12-start)-(12-start)//2)
    else:
        builder.adjust(6,5)
    builder.row(InlineKeyboardButton(text=Buttons.CANCEL,callback_data=NavCB(to="stats_choose").pack()))
    return builder.as_markup()

def cancel_kb(back,kind = "expense"):
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.CANCEL,callback_data=NavCB(to=back,kind=kind))
    return builder.as_markup()

def confirm(to_yes,to_no,kind = "expense",category_id: int | None = None):
    builder = InlineKeyboardBuilder()
    # With a category_id, "Да" carries the id itself (CategoryCB, purpose=to_yes) instead of
    # leaving it in FSM for the confirm handler -- a "Меню" tap in between can't lose it.
    # NavCB is deliberately not given an id field: that would change the packed format of
    # every nav: button already sitting in users' chats, as NavCB.mode did in 1.5.1.
    if category_id is not None:
        yes_cb = CategoryCB(id=category_id,purpose=to_yes,kind=kind)
    else:
        yes_cb = NavCB(to=to_yes,kind=kind)
    builder.button(text=Buttons.YES,callback_data=yes_cb)
    builder.button(text=Buttons.NO,callback_data=NavCB(to=to_no,kind=kind))
    builder.adjust(2)
    return builder.as_markup()


def categories_kb(categories, page: int,max_page: int,purpose:str,kind="expense",mode="today"):
    builder = InlineKeyboardBuilder()
    for c in categories:
        cb = CategoryCB(id=c["category_id"], purpose=purpose, kind=kind, mode=mode)
        if purpose == "delete":
            builder.button(text=(c["name"] + f"{"*" if c["is_archived"] == 1 else ""}"), callback_data=cb)
        else:
            builder.button(text=(c["name"]), callback_data=cb)
    prev_cb = CatPageCB(page=(int(page) - 1), purpose=purpose, kind=kind, mode=mode)
    next_cb = CatPageCB(page=(int(page) + 1), purpose=purpose, kind=kind, mode=mode)
    prev_btn = InlineKeyboardButton(text="<-", callback_data=prev_cb.pack())
    next_btn = InlineKeyboardButton(text="->", callback_data=next_cb.pack())
    builder.adjust(2)
    if max_page > 1:
        if page == 1:
            builder.row(next_btn)
        elif page == max_page:
            builder.row(prev_btn)
        else:
            builder.row(prev_btn,next_btn)
    if purpose == "expense" or purpose == "income":
        builder.row(InlineKeyboardButton(text="Меню",callback_data=NavCB(to="menu",kind=kind).pack()))
    else:
        builder.row(InlineKeyboardButton(text="Отмена",callback_data=NavCB(to="edit",kind=kind).pack()))

    return builder.as_markup()

def edit_archived_kb(kind = "expense"):
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.ARCHIVE,callback_data=NavCB(to="archive",kind=kind))
    builder.button(text=Buttons.DEARCHIVE,callback_data=NavCB(to="dearchive",kind=kind))
    builder.adjust(2)
    return builder.as_markup()

def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.ADD_EXPENSE,callback_data=NavCB(to="expense"))
    builder.button(text=Buttons.ADD_INCOME,callback_data=NavCB(to="income"))
    builder.button(text=Buttons.STATS,callback_data=NavCB(to="stats"))
    builder.button(text=Buttons.HISTORY,callback_data=NavCB(to="history"))
    builder.button(text=Buttons.EDIT_EXPENSE_CATEGORIES,callback_data=NavCB(to="edit"))
    builder.button(text=Buttons.EDIT_INCOME_CATEGORIES, callback_data=NavCB(to="edit", kind="income"))
    builder.button(text=Buttons.SETTINGS,callback_data=NavCB(to="set"))
    builder.button(text=Buttons.CODE,callback_data=NavCB(to="code"))
    builder.button(text=Buttons.ABOUT,callback_data=NavCB(to="about"))
    builder.adjust(2)
    return builder.as_markup()

def history_kb(page: int, max_page: int, kind: str | None = None, who: str = "all", sort: str = "id"):
    builder = InlineKeyboardBuilder()
    who_next, who_label = HISTORY_CYCLES["who"][who]
    kind_next, kind_label = HISTORY_CYCLES["kind"][kind]
    sort_next, sort_label = HISTORY_CYCLES["sort"][sort]
    # Toggle row: label shows the CURRENT value, callback_data carries the NEXT value
    # (plus page=1 -- changing a filter mid-page could otherwise land past the new max_page).
    builder.row(
        InlineKeyboardButton(
            text=who_label, callback_data=HistoryPageCB(page=1, kind=kind, who=who_next, sort=sort).pack()
        ),
        InlineKeyboardButton(
            text=kind_label, callback_data=HistoryPageCB(page=1, kind=kind_next, who=who, sort=sort).pack()
        ),
        InlineKeyboardButton(
            text=sort_label, callback_data=HistoryPageCB(page=1, kind=kind, who=who, sort=sort_next).pack()
        ),
    )
    prev_cb = HistoryPageCB(page=page - 1, kind=kind, who=who, sort=sort)
    next_cb = HistoryPageCB(page=page + 1, kind=kind, who=who, sort=sort)
    prev_btn = InlineKeyboardButton(text=Buttons.PREV_PAGE, callback_data=prev_cb.pack())
    next_btn = InlineKeyboardButton(text=Buttons.NEXT_PAGE, callback_data=next_cb.pack())
    if max_page > 1:
        if page == 1:
            builder.row(next_btn)
        elif page == max_page:
            builder.row(prev_btn)
        else:
            builder.row(prev_btn,next_btn)
    builder.row(InlineKeyboardButton(text=Buttons.MENU,callback_data=NavCB(to="menu").pack()))
    return builder.as_markup()

def added_confirm_kb(kind="expense",mode="today"):
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.ADD_MORE_SAME_DATE,callback_data=NavCB(to="add_again",kind=kind,mode=mode))
    # Same callback_data as main_menu()'s "➖ Трата"/"➕ Доход" -- lands in choose_add_date,
    # so the date picker is reused as-is instead of getting a second handler.
    builder.button(text=Buttons.ADD_OTHER_DATE,callback_data=NavCB(to=kind))
    builder.button(text=Buttons.MENU,callback_data=NavCB(to="menu"))
    builder.adjust(1)
    return builder.as_markup()

def to_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.MENU,callback_data=NavCB(to="menu"))
    return builder.as_markup()

def code_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.ROTATE_CODE,callback_data=NavCB(to="rotate_code"))
    builder.button(text=Buttons.MENU,callback_data=NavCB(to="menu"))
    builder.adjust(1)
    return builder.as_markup()

def settings_kb(is_admin=False):
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.TIMEZONE,callback_data=NavCB(to="timez"))
    builder.button(text=Buttons.NICKNAME,callback_data=NavCB(to="nickname"))
    if is_admin:
        builder.button(text=Buttons.SANDBOX,callback_data=NavCB(to="sandbox"))  # sandbox, gated (SEC-8)
    builder.button(text=Buttons.MENU,callback_data=NavCB(to="menu"))
    builder.adjust(2)
    return builder.as_markup()

def timezone_kb(current: str = "", back: str = "set"):
    b = InlineKeyboardBuilder()
    for i, (city, zone) in enumerate(TIMEZONES):
        mark = "✅ " if zone == current else ""
        b.button(text=f"{mark}{city}", callback_data=TzCB(index=i))
    b.adjust(3)
    b.row(InlineKeyboardButton(text=Buttons.OTHER_CITY, callback_data=TzCB().pack()))
    b.row(InlineKeyboardButton(text=Buttons.BACK, callback_data=NavCB(to=back).pack()))
    return b.as_markup()

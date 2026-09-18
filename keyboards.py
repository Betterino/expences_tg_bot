
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from callback import OnboardCB, CategoryCB,CatPageCB,NavCB,MonthCB,RangeCB,StatsCB,AddCB, TzCB, HistoryPageCB
from utils import shift_month
from constants import TIMEZONES
from texts import Buttons, MONTHS

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
    prev_btn = InlineKeyboardButton(text=Buttons.PREV_PAGE,callback_data=StatsCB(year=prev_year,month=prev_month).pack())
    next_btn = InlineKeyboardButton(text=Buttons.NEXT_PAGE,callback_data=StatsCB(year=next_year,month=next_month).pack())
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

def confirm(to_yes,to_no,kind = "expense"):
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.YES,callback_data=NavCB(to=to_yes,kind=kind))
    builder.button(text=Buttons.NO,callback_data=NavCB(to=to_no,kind=kind))
    builder.adjust(2)
    return builder.as_markup()


def categories_kb(categories, page: int,max_page: int,purpose:str,kind="expense"):
    builder = InlineKeyboardBuilder()
    for c in categories:
        if purpose == "delete":
            builder.button(text=(c["name"] + f"{"*" if c["is_archived"] == 1 else ""}"), callback_data=CategoryCB(id=c["category_id"],purpose=purpose,kind=kind))
        else:
            builder.button(text=(c["name"]), callback_data=CategoryCB(id=c["category_id"],purpose=purpose,kind=kind))
    prev_btn = InlineKeyboardButton(text="<-",callback_data=CatPageCB(page=(int(page)-1),purpose=purpose,kind=kind).pack())
    next_btn = InlineKeyboardButton(text="->",callback_data=CatPageCB(page=(int(page)+1),purpose=purpose,kind=kind).pack())
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
    builder.adjust(2)
    return builder.as_markup()

def history_kb(page: int, max_page: int, kind: str | None = None):
    builder = InlineKeyboardBuilder()
    prev_btn = InlineKeyboardButton(text=Buttons.PREV_PAGE,callback_data=HistoryPageCB(page=page-1,kind=kind).pack())
    next_btn = InlineKeyboardButton(text=Buttons.NEXT_PAGE,callback_data=HistoryPageCB(page=page+1,kind=kind).pack())
    if max_page > 1:
        if page == 1:
            builder.row(next_btn)
        elif page == max_page:
            builder.row(prev_btn)
        else:
            builder.row(prev_btn,next_btn)
    builder.row(InlineKeyboardButton(text=Buttons.MENU,callback_data=NavCB(to="menu").pack()))
    return builder.as_markup()

def added_confirm_kb(kind="expense"):
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.ADD_MORE_SAME_DATE,callback_data=NavCB(to="add_again",kind=kind))
    builder.button(text=Buttons.MENU,callback_data=NavCB(to="menu"))
    builder.adjust(1)
    return builder.as_markup()

def to_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.MENU,callback_data=NavCB(to="menu"))
    return builder.as_markup()

def settings_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.TIMEZONE,callback_data=NavCB(to="timez"))
    builder.button(text=Buttons.NICKNAME,callback_data=NavCB(to="nickname"))
    builder.button(text=Buttons.SANDBOX,callback_data=NavCB(to="sandbox"))  # sandbox
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
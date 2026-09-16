
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from callback import OnboardCB, CategoryCB,CatPageCB,NavCB,MonthCB,RangeCB,StatsCB,AddCB, TzCB
from utils import shift_month
from constants import MONTHS_LIST, TIMEZONES

def choose_range_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="За год", callback_data=RangeCB(year_month="year"))
    builder.button(text="За месяц", callback_data=RangeCB(year_month="month"))
    builder.button(text="За несколько месяцев", callback_data=RangeCB(year_month="months"))
    builder.button(text="Отмена",callback_data=NavCB(to="stats"))
    builder.adjust(1)
    return builder.as_markup()

def edit_kb(kind = "expense"):
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить категорию",callback_data=NavCB(to="edit_cat",kind=kind))
    if kind == "expense":
        builder.button(text="Изменить максимум",callback_data=NavCB(to="edit_max",kind=kind))
    builder.button(text="Изменить название",callback_data=NavCB(to="edit_name",kind=kind))
    builder.button(text="Архивировать категорию",callback_data=NavCB(to="edit_arch",kind=kind))
    builder.button(text="Удалить категорию",callback_data=NavCB(to="edit_delete",kind=kind))
    #builder.button(text="Последовательность категорий")
    builder.button(text="В меню",callback_data=NavCB(to="menu"))
    builder.adjust(1)
    return builder.as_markup()


def date_expense_kb(kind):
    builder = InlineKeyboardBuilder()
    builder.button(text="Today",callback_data=AddCB(mode="today",kind=kind))
    builder.button(text="Yesterday",callback_data=AddCB(mode="yesterday",kind=kind))
    builder.button(text="Input date",callback_data=AddCB(mode="date",kind=kind))
    builder.button(text="Menu",callback_data=NavCB(to="menu"))
    builder.adjust(1)
    return builder.as_markup()

def stats_kb(year,month):
    builder = InlineKeyboardBuilder()
    builder.button(text="Выбрать другой период",callback_data=NavCB(to="stats_choose"))
    builder.button(text="В меню",callback_data=NavCB(to="menu"))
    builder.adjust(1)
    prev_year, prev_month = shift_month(year,month,-1)
    next_year, next_month = shift_month(year,month,1)
    prev_btn = InlineKeyboardButton(text="<-",callback_data=StatsCB(year=prev_year,month=prev_month).pack())
    next_btn = InlineKeyboardButton(text="->",callback_data=StatsCB(year=next_year,month=next_month).pack())
    builder.row(prev_btn,next_btn)
    return builder.as_markup()

def special_stats_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Выбрать другой период",callback_data=NavCB(to="stats_choose"))
    builder.button(text="В меню",callback_data=NavCB(to="menu"))
    return builder.as_markup()

def onboarding_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Создать свой бюджет", callback_data=OnboardCB(action="create"))
    builder.button(text="Присоединиться к чужому", callback_data=OnboardCB(action="join"))
    builder.adjust(1)
    return builder.as_markup()

def months_kb(purpose:str,start = 0):
    builder = InlineKeyboardBuilder()
    for i in range(start,11):
        builder.button(text=MONTHS_LIST[i], callback_data=MonthCB(month=i,purpose=purpose))
    if purpose != "from":
        builder.button(text=MONTHS_LIST[11],callback_data=MonthCB(month=11,purpose=purpose))
        builder.adjust((12-start)//2,(12-start)-(12-start)//2)
    else:
        builder.adjust(6,5)
    builder.row(InlineKeyboardButton(text="Отмена",callback_data=NavCB(to="stats_choose").pack()))
    return builder.as_markup()

def cancel_kb(back,kind = "expense"):
    builder = InlineKeyboardBuilder()
    builder.button(text="Отмена",callback_data=NavCB(to=back,kind=kind))
    return builder.as_markup()

def confirm(to_yes,to_no,kind = "expense"):
    builder = InlineKeyboardBuilder()
    builder.button(text="Да",callback_data=NavCB(to=to_yes,kind=kind))
    builder.button(text="Нет",callback_data=NavCB(to=to_no,kind=kind))
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
    builder.button(text="Архивируем",callback_data=NavCB(to="archive",kind=kind))
    builder.button(text="Достаем из архива",callback_data=NavCB(to="dearchive",kind=kind))
    return builder.as_markup()

def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить Трату",callback_data=NavCB(to="expense"))
    builder.button(text="Добавить Доход",callback_data=NavCB(to="income"))
    builder.button(text="Статистика",callback_data=NavCB(to="stats"))
    builder.button(text="Редактировать Траты",callback_data=NavCB(to="edit"))
    builder.button(text="Редактировать Доходы", callback_data=NavCB(to="edit", kind="income"))
    builder.button(text="Настройки",callback_data=NavCB(to="set"))
    builder.button(text="Код-приглашение",callback_data=NavCB(to="code"))
    builder.adjust(1)
    return builder.as_markup()

def to_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Меню",callback_data=NavCB(to="menu"))
    return builder.as_markup()

def settings_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Таймзона",callback_data=NavCB(to="timez"))
    builder.button(text="Меню",callback_data=NavCB(to="menu"))
    return builder.as_markup()

def timezone_kb(current: str = "", back: str = "set"):
    b = InlineKeyboardBuilder()
    for i, (city, zone) in enumerate(TIMEZONES):
        mark = "✅ " if zone == current else ""
        b.button(text=f"{mark}{city}", callback_data=TzCB(index=i))
    b.adjust(3)
    b.row(InlineKeyboardButton(text="Другой город", callback_data=TzCB().pack()))
    b.row(InlineKeyboardButton(text="Назад", callback_data=NavCB(to=back).pack()))
    return b.as_markup()
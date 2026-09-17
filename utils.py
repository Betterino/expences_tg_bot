from calendar import monthrange
from datetime import datetime, date
from zoneinfo import ZoneInfo
from constants import PER_PAGE
def parse_amount(text: str) -> int|None:
    try:
        text = text.replace(".",",")
        values = text.split(",")

        if len(values) > 2:
            return None
        else:
            if len(values) > 1:
                if len(values[1]) > 2:
                    return None
                else:
                    frac = values[1].ljust(2, "0")
                    return int(values[0]) *100 + int(frac)
            else:
                return int(values[0]) * 100
    except(ValueError, AttributeError):
        return None
    
def format_tx_date(date_str: str) -> str:
    return date.fromisoformat(date_str).strftime("%d.%m.%Y")

def format_money(value: int) -> str:
    rubles = value // 100
    kopeiki = value % 100
    if kopeiki > 0:
        text = f"{rubles},{kopeiki:02d}"
    else: 
        text = str(rubles)
    return text

def stats_bounds(start_year,start_month,end_year,end_month) ->tuple[str,str]:
    return f"{start_year}-{start_month:02d}-01", f"{end_year}-{end_month:02d}-{monthrange(end_year,end_month)[1]:02d}"

def year_bounds(year) -> tuple[str,str]:
    return f"{year}-01-01",f"{year}-12-31"

def shift_month(year,month,delta) -> tuple[int,int]:
    new_month = (year * 12 + month + delta - 1) % 12 + 1
    new_year = ((year * 12 + month + delta) - new_month) // 12
    return new_year,new_month

def calc_page(categories,page):
    size = len(categories)
    new_categories = []
    i = PER_PAGE*(page-1)
    while i < min(size,PER_PAGE*(page)):
        new_categories.append(categories[i])
        i += 1
    return new_categories

def today(tz_name: str):
    return datetime.now(ZoneInfo(tz_name)).date()

def create_stats_text(start,end,total_e,expense,income,total_i):
    text = ""
    text += f"Статистика за период\n{start} - {end}\n<code>{"Название":<18}|{"Траты":<12}|{"Максимум":<12}\n"
    for r in expense:
        if r["maximum"] != 0:
            text += f"{r["name"]:<18}|{format_money(r["total"]):<12}|{format_money(r["maximum"]):<12}\n"
        else:
            text += f"{r["name"]:<18}|{format_money(r["total"]):<12}\n"
    text += f"Всего: {format_money(total_e):<12}"
    text += "</code>\n"
    text += f"\n<code>{"Название":<18}|{"Доходы":<12}\n"
    for r in income:
            text += f"{r["name"]:<18}|{format_money(r["total"]):<12}\n"
    text += f"Всего: {format_money(total_i):<12}"
    diff = total_i - total_e
    text += f"\nИтого: {format_money(diff):<12} У вас {"Избыток" if diff >= 0 else "Убыток" }"
    return text+"</code>"

def parse_categories_edit(categories,kind = "expense"):
    cats = ""
    archs = ""
    for row in categories:
        if row["is_archived"] == 0:
            if kind == "expense":
                cats += f"{row["name"]:<18} | {format_money(row["maximum"]):<12}\n"
            else:
                cats += f"{row["name"]:<18}\n"
        else:
            if kind == "expense":
                archs += f"{row["name"]:<18} | {format_money(row["maximum"]):<12}\n"
            else:
                archs += f"{row["name"]:<18}\n"
    if kind == "expense":
        final_txt = f"Активные Категории:\n<code>{"Название":<18}" + f"| {"Максимум":<12}\n" + cats + f"</code>Архивные Категории:\n<code>{"Название":<18} | {"Максимум":<12}\n" + archs + "</code>"
    else:
        final_txt = f"Активные Категории:\n<code>{"Название":<18}\n" + cats + f"</code>Архивные Категории:\n<code>{"Название":<18}\n" + archs + "</code>"
    return final_txt

def parse_date(date_str:str,timezone):
    now = today(timezone)
    arr = date_str.strip().split(".")
    try:
        day = int(arr[0])
        month = int(arr[1])
    except ValueError:
        return None
    for year in (now.year, now.year - 1):
        try:
            guess = date(year, month, day)
        except ValueError:
            continue
        if guess <= now:
            return guess
    return None
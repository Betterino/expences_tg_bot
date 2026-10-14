import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage, InlineKeyboardMarkup, Message

import richtext
from db import Database
from keyboards import categories_kb, edit_kb, main_menu, special_stats_kb, stats_kb
from texts import Errors, Screens
from utils import calc_page, page_count, stats_bounds
from views import TableData, categories_view, menu_view, stats_view

logger = logging.getLogger(__name__)

# CallbackQuery.message is Message | InaccessibleMessage | None: None for inline-mode
# buttons, InaccessibleMessage when Telegram no longer gives the bot that message
# (Bot API: "deleted or otherwise inaccessible"). Every callback handler passes
# callback.message straight in, so the check lives here, once, instead of at 34 call
# sites -- an AttributeError would reach @dp.error(), whose own answer to the query
# then fails too ("query is too old").
MaybeMessage = Message | InaccessibleMessage | None


def _usable(message: MaybeMessage) -> bool:
    # A negative check on purpose: tests/fakes.py's FakeMessage isn't an aiogram Message,
    # and InaccessibleMessage is a sibling class of Message, not a subclass.
    if message is None or isinstance(message, InaccessibleMessage):
        logger.warning("нечего редактировать: message=%s", type(message).__name__)
        return False
    return True


async def edit_rich(message: MaybeMessage, blocks: list[richtext.Block], reply_markup=None) -> None:
    """Swallow only "message is not modified" -- Telegram rejects an editMessageText
    whose text AND markup are byte-identical to what is already on screen, which is
    exactly what re-tapping the currently selected month/page produces. Unhandled it
    reaches @dp.error() and shows "Что-то сломалось" for a no-op."""
    if not _usable(message):
        return
    try:
        await message.edit_text(rich_message=richtext.message(blocks), reply_markup=reply_markup)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise


async def answer_rich(message: MaybeMessage, blocks: list[richtext.Block], reply_markup=None) -> None:
    if not _usable(message):
        return
    await message.answer_rich(rich_message=richtext.message(blocks), reply_markup=reply_markup)


async def edit_text(message: MaybeMessage, text: str, reply_markup=None) -> None:
    """Plain-text twin of edit_rich -- same "message is not modified" swallow."""
    if not _usable(message):
        return
    try:
        await message.edit_text(text=text, reply_markup=reply_markup)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise


async def show_menu(message: MaybeMessage, edit: bool) -> None:
    """The one place that renders the menu screen -- every entry point (/start,
    /cancel, /help, the Меню button, a stale multi-add state) goes through this
    instead of building its own rich_message, so the collapsible help block
    (views.menu_view) never drifts between call sites."""
    blocks = menu_view()
    if edit:
        await edit_rich(message, blocks, reply_markup=main_menu())
    else:
        await answer_rich(message, blocks, reply_markup=main_menu())


### Stat screen
async def load_stats(db: Database, budget_id: int, start: str, end: str) -> TableData:
    return TableData(
        start=start,
        end=end,
        total_e=await db.stats_total(budget_id, start, end, "expense"),
        expense=await db.expense_by_category(budget_id, start, end),
        income=await db.income_by_category(budget_id, start, end),
        total_i=await db.stats_total(budget_id, start, end, "income"),
    )


async def render_special_stats_screen(
    year_start, month_start, year_end, month_end, db: Database, budget_id, callback: CallbackQuery
):
    start, end = stats_bounds(year_start, month_start, year_end, month_end)
    data = await load_stats(db, budget_id, start, end)
    await edit_rich(callback.message, stats_view(data), reply_markup=special_stats_kb())

async def render_stats_screen(year,month,db: Database, budget_id, callback: CallbackQuery):
    start, end = stats_bounds(year, month, year, month)
    data = await load_stats(db, budget_id, start, end)
    await edit_rich(callback.message, stats_view(data), reply_markup=stats_kb(year, month))


async def build_categories_screen(
    db: Database, budget_id: int, purpose: str, page: int, kind: str = "expense", mode: str = "today"
) -> tuple[str, InlineKeyboardMarkup]:
    if purpose == "dearchive":
        categories = await db.list_archived_categories(budget_id,kind)
    elif purpose == "delete":
        categories = await db.list_all_categories(budget_id,kind)
    else:
        categories = await db.list_active_categories(budget_id,kind)
    max_page = page_count(len(categories))
    categories = calc_page(categories,page)
    text = Screens.CATEGORY_PICKER[purpose]
    text += Screens.PAGE.format(page=page, max_page=max_page)
    if len(categories) == 0:
        text = Errors.BAD_PAGE
    return text, categories_kb(categories,page,max_page,purpose,kind,mode)

async def render_categories_screen(
    callback: CallbackQuery,
    db: Database,
    budget_id: int,
    purpose: str,
    page: int,
    kind: str = "expense",
    mode: str = "today",
):
    text, markup = await build_categories_screen(db, budget_id, purpose, page, kind, mode)
    await edit_text(callback.message, text, reply_markup=markup)

async def build_edit_screen(
    db: Database, budget_id: int, prefix: str = "", kind: str = "expense"
) -> list[richtext.Block]:
    categories = await db.all_categories(budget_id,kind)
    return categories_view(categories, kind, prefix)

async def render_edit_screen(
    callback: CallbackQuery,
    db: Database,
    budget_id: int,
    state: FSMContext,
    prefix: str,
    kind: str = "expense",
):
    await state.clear()
    blocks = await build_edit_screen(db, budget_id, prefix, kind)
    await edit_rich(callback.message, blocks, reply_markup=edit_kb(kind))

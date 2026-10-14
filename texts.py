MONTHS = ["Янв.", "Фев.", "Март", "Апр.", "Май", "Июнь", "Июль", "Авг.", "Сен.", "Окт.", "Ноя.", "Дек."]


class Buttons:
    ADD_EXPENSE = "➖ Трата"
    ADD_INCOME = "➕ Доход"
    STATS = "📊 Статистика"
    HISTORY = "🧾 История"
    EDIT_EXPENSE_CATEGORIES = "✏️ Кат. трат"
    EDIT_INCOME_CATEGORIES = "✏️ Кат. доходов"
    SETTINGS = "⚙️ Настройки"
    CODE = "🔗 Код"
    ROTATE_CODE = "🔄 Обновить код"

    ADD_CATEGORY = "➕ Добавить"
    EDIT_MAXIMUM = "💰 Максимум"
    EDIT_NAME = "✏️ Название"
    ARCHIVE_CATEGORY = "📦 Архив"
    DELETE_CATEGORY = "🗑 Удалить"
    MENU = "Меню"
    CANCEL = "Отмена"

    YES = "Да"
    NO = "Нет"

    ARCHIVE = "Архивируем"
    DEARCHIVE = "Достаем из архива"

    CREATE_BUDGET = "Создать свой бюджет"
    JOIN_BUDGET = "Присоединиться к чужому"

    BY_YEAR = "За год"
    BY_MONTH = "За месяц"
    BY_MONTHS = "За несколько месяцев"
    CHOOSE_OTHER_PERIOD = "Выбрать другой период"

    PREV_PAGE = "<-"
    NEXT_PAGE = "->"

    TODAY = "Сегодня"
    YESTERDAY = "Вчера"
    INPUT_DATE = "Указать дату"

    ADD_MORE_SAME_DATE = "➕ Добавить ещё на эту дату"
    ADD_OTHER_DATE = "📅 Добавить на другую дату"

    TIMEZONE = "Таймзона"
    NICKNAME = "Никнейм"
    OTHER_CITY = "Другой город"
    BACK = "Назад"
    SANDBOX = "🧪 Тест"  # sandbox

    ABOUT = "ℹ️ О боте"

    # История: labels показывают ТЕКУЩЕЕ значение фильтра (экран сам себя описывает),
    # а callback_data кнопки несёт СЛЕДУЮЩее значение цикла (constants.HISTORY_CYCLES).
    HISTORY_WHO_ALL = "👥 Все"
    HISTORY_WHO_MINE = "👤 Мои"
    HISTORY_KIND_ALL = "🔀 Всё"
    HISTORY_KIND_EXPENSE = "➖ Траты"
    HISTORY_KIND_INCOME = "➕ Доходы"
    HISTORY_SORT_BY_ID = "🆕 По добавлению"
    HISTORY_SORT_BY_DATE = "📅 По дате"


class Screens:
    CATEGORY_PICKER = {
        "expense": "Выберите категорию для трат\n",
        "edit": "Выберите категорию которую редактируем\n",
        "changemax": "Выберите категорию чей максимум меняем\n",
        "changename": "Выберите категорию чье название меняем\n",
        "delete": "Выберите категорию которую удаляем\n* - около категории значит она в архиве\n",
        "archive": "Выберите категорию которую архивируем\n",
        "income": "Выберите категорию дохода\n",
        "dearchive": "Выберите категорию которую деархивируем\n",
    }
    PAGE = "Страница {page:2d}/{max_page:2d}"
    CANCELLED = "Отменил"
    MENU_TITLE = "Это меню"
    MENU_HELP_SUMMARY = "❓ Что делает каждая кнопка"
    MENU_HELP_COLUMNS = ["Кнопка", "Что делает"]
    # Keyed on Buttons.* so a label rename can never desync the help text from the
    # keyboard -- tests/test_menu.py asserts this list covers exactly main_menu()'s buttons.
    MENU_HELP = [
        (Buttons.ADD_EXPENSE, "Записать трату: дата → категория → сумма"),
        (Buttons.ADD_INCOME, "Записать доход тем же путём"),
        (Buttons.STATS, "Статистика трат и доходов за период"),
        (Buttons.HISTORY, "Лента всех записей с фильтрами и сортировкой"),
        (Buttons.EDIT_EXPENSE_CATEGORIES, "Добавить, переименовать, задать максимум или удалить категорию"),
        (Buttons.EDIT_INCOME_CATEGORIES, "То же самое для категорий доходов"),
        (Buttons.SETTINGS, "Часовой пояс, никнейм и прочие настройки"),
        (Buttons.CODE, "Код-приглашение в общий бюджет"),
        (Buttons.ABOUT, "Версия бота и что нового"),
    ]
    CHOOSE_RANGE = (
        "Выберите за какой период будет выбрана статистика\n"
        "За определенный год\n"
        "За определенный месяц в этом году\n"
        "За несколько месяцев в этом году"
    )


class Onboarding:
    START_TEXT = (
        "Добро пожаловать в Вашу свинку-копилку!\n"
        "С ней Вы можете записывать свои траты и задавать максимум их использования при "
        "необходимости, отслеживать их и просматривать статистику за период использования копилки.\n"
        "В начале каждого месяца мы будем отправлять Вам статистику за прошедший месяц. Вы так же "
        "можете настроить напоминания в течение дня после создания копилки в настройках.\n"
        "Давайте определимся: хотите вести совместный бюджет с близкими или создать свою личную "
        "свинку-копилку?"
    )
    ADD_CODE_TEXT = (
        "Отлично! Попросите владельца другой копилки выбрать в меню код-приглашение и отправить "
        "сгенерированный код Вам. Затем отправьте сюда в чат этот код и мы отправим Вас в меню в "
        "общую свинку-копилку!"
    )
    GET_CODE_TEXT = (
        "Ваш пригласительный код для близких сгенерирован! Отправьте его человеку, который хочет "
        "присоединиться к Вашему бюджету, чтобы он мог отправить его в чат. \n"
        "Код копируется при нажатии -> "
    )
    ROTATED_CODE_TEXT = """Старый код больше не действует. Новый код для приглашения близких: """
    CREATE_BUDGET = (
        "Давайте настроим Вашу свинку-копилку! \n"
        "Изначально мы предлагаем использовать следующие категории трат без ограничений:\n"
        "Продукты;\n"
        "Здоровье;\n"
        "Жилье и ЖКУ;\n"
        "Транспорт;\n"
        "Связь и подписки;\n"
        "Кафе и рестораны;\n"
        "Одежда;\n"
        "Развлечения;\n"
        "Прочее.\n"
        "\n"
        "Хотите ли Вы сейчас добавить другие категории? \n"
        "P.S. Вы можете отредактировать категории и их максимумы после создания копилки."
    )
    NO_SUCH_BUDGET = "Такого бюджета нет"
    JOINED = "Успешно присоединены!"


class Categories:
    ADDED = "Добавил {name}\nХотите добавить еще?\n"
    RENAMED = "Изменил {name}\n\n"
    DELETED = "Удалил\n\n"
    DONE = "Успешно!\n"
    MAX_CHANGED = "Изменил\n\n"
    PROMPT_MAXIMUM = "Хотите ли вы добавить максимум к этой категории?"
    NAME_EXISTS = "Категория с таким названием уже есть, вы уверены что хотите добавить?"
    ASK_NEW_NAME = "Введите новое название категории"
    ASK_MAX = "Введите новый максимум категории"
    EMPTY_NAME = "Выприслали пустое сообщение, попробуйте еще раз"
    CHOOSE_ARCHIVE = "Выберете архивируем или достаем из архива"
    DELETE_CONFIRM = (
        "Вы уверены?\n"
        "Если вы записывали траты в эту категорию, они останутся в статистике, "
        "но будут без категории"
    )
    ACTIVE_HEADER = "Активные Категории:"
    ARCHIVED_HEADER = "Архивные Категории:"
    NAME_COLUMN = "Название"
    MAX_COLUMN = "Максимум"


class Errors:
    NO_BUDGET = "Сначала создай бюджет: /start"
    BAD_AMOUNT = "Не понял число"
    BAD_DATE = "Не понял дату, попробуй ещё раз"
    BAD_PAGE = "Категорий для этого действия нет"
    BAD_YEAR = "Не понял год, попробуй ещё раз"
    SOMETHING_BROKE = "Что-то сломалось, попробуйте ещё раз"
    # Deliberately does not distinguish "doesn't exist" from "not yours" -- both are the
    # same response to a category id that isn't a legitimate button in this budget.
    NOT_FOUND = "Категория не найдена, попробуйте ещё раз"
    # A crafted (not tapped) CallbackData value outside the field's real domain --
    # e.g. a timezone index or month that doesn't correspond to any button we render.
    BAD_SELECTION = "Некорректный выбор, попробуйте ещё раз"
    # A multi-step flow whose FSM data is gone -- a "Меню" tap (state.clear()) came first,
    # or the button belongs to an older screen still sitting in the chat (handlers/flow.py).
    FLOW_EXPIRED = "Действие устарело, начните заново"
    # A button no handler recognizes -- usually one packed in an older CallbackData format.
    STALE_BUTTON = "Кнопка устарела, откройте Меню"


class Prompts:
    AMOUNT = {
        "expense": "Сколько потратил?\nМожно сложить: 100+250+80",
        "income": "Сколько получил?\nМожно сложить: 100+250+80",
    }
    CHOOSE_DATE_ADD = {
        "expense": "Выберите когда хотите добавить трату\nСейчас: {now}",
        "income": "Выберите когда хотите добавить доход\nСейчас: {now}",
    }
    INPUT_DATE_ADD = {
        "expense": "В какую дату произошла трата?\nДля корректной работы напишите дату в формате: ДД.ММ",
        "income": "В какую дату пришёл доход?\nДля корректной работы напишите дату в формате: ДД.ММ",
    }


class Stats:
    ADDED = "Записал {amount}"
    ADDED_SUM = "Записал {parts} = {amount}"
    TOTAL_COLUMN = "Траты"
    INCOME_COLUMN = "Доходы"
    SURPLUS = "Избыток"
    DEFICIT = "Убыток"
    GOT_MONTH = "Получил {month}\nВыберете месяц c которым будет заканчиваться статистика"
    CHOOSE_YEAR = "Выберите год за который будет выведена статистика"
    CHOOSE_MONTH = "Выберите месяц за который будет выведена статистика"
    CHOOSE_START_MONTH = "Выберите месяц c которого будет начинаться статистика"


class History:
    EMPTY = "Пока нет ни одной записи"
    HEADER = "История\n" + Screens.PAGE
    # Header filter labels (plain, no emoji -- those live on the buttons in Buttons.*).
    WHO_LABELS = {"all": "Все", "mine": "Мои"}
    KIND_LABELS = {None: "Всё", "expense": "Траты", "income": "Доходы"}
    SORT_LABELS = {"id": "По добавлению", "date": "По дате"}
    KTO_COLUMN = "Кто"
    DATE_COLUMN = "Дата"
    AMOUNT_COLUMN = "Сумма"
    CATEGORY_COLUMN = "Категория"
    NO_CATEGORY = "Без категории"


class Settings:
    TITLE = "Настройки"
    TZ_CONFIRM = "Часовой пояс: {zone}\nСейчас у тебя {now} — верно?"
    TZ_MANUAL_PROMPT = (
        "Напиши название зоны, например <code>Europe/Rome</code>\n"
        "Список: en.wikipedia.org/wiki/List_of_tz_database_time_zones"
    )
    TZ_UNKNOWN = "Не знаю такой зоны. Формат: Europe/Rome"
    TZ_SAVED = "Готово. Сейчас у тебя {now}"
    NO_NICKNAME = "не задан"
    NICKNAME_PROMPT = "Текущий никнейм: {current}\nНапиши новый (до 20 символов)"
    NICKNAME_EMPTY = "Никнейм не может быть пустым, попробуй ещё раз"
    NICKNAME_SAVED = "Готово. Твой никнейм: {nickname}"


class About:
    TITLE = "О боте"
    VERSION_LINE = "Версия {version}"
    # Написано руками, а не выведено из CHANGELOG.md -- пользователь просил "очень
    # кратко", а парсер markdown внутри бота того не стоит. tests/test_changelog.py
    # проверяет единственный дрифт, который важен: версия совпадает в обоих местах.
    SUMMARY = (
        "Новое в этой версии:\n"
        "• Обновление кода-приглашения\n"
        "• Отрицательные/нулевые суммы больше не принимаются\n"
        "• Надёжнее работа с категориями между бюджетами\n"
        "• Бот больше не роняет экран на испорченных ссылках"
    )
    CHANGELOG_LINK = "Полный список изменений — в описании бота"

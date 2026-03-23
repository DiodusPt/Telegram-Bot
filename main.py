import telebot
import sqlite3
from telebot import types
from config import TOKEN

bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect('inventory.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS cabinets
                 (id INTEGER PRIMARY KEY, 
                 number TEXT UNIQUE NOT NULL)''')

    conn.execute('''CREATE TABLE IF NOT EXISTS items
                 (id INTEGER PRIMARY KEY,
                 cabinet_id INTEGER,
                 name TEXT NOT NULL,
                 quantity INTEGER DEFAULT 1,
                 description TEXT,
                 model TEXT,
                 manufacturer TEXT,
                 serial_number TEXT,
                 FOREIGN KEY (cabinet_id) REFERENCES cabinets (id))''')
    conn.commit()
    conn.close()

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("📦 Добавить кабинет")
    btn2 = types.KeyboardButton("➕ Добавить объект")
    btn3 = types.KeyboardButton("👀 Посмотреть содержимое")
    btn4 = types.KeyboardButton("🔍 Расширенный поиск")
    btn5 = types.KeyboardButton("🗑️ Удалить объект")
    btn6 = types.KeyboardButton("⛔ Удалить кабинет")
    btn7 = types.KeyboardButton("ℹ️ Справка")
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5, btn6)
    markup.add(btn7)
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_first_name = message.from_user.first_name
    bot.send_message(
        message.chat.id,
        f"Приветствую, {user_first_name}! Я бот-инвентаризатор и я помогу Вам вести инвентарный учёт Вашей организации!",
        reply_markup=main_menu()
    )

@bot.message_handler(commands=['help'])
@bot.message_handler(commands=['help'])
def help(message):
    help_text = (
        "🤖 <b>Справка по боту-инвентаризатору</b>\n\n"
        "Используйте кнопки меню или команды:\n\n"
        "📦 <b>Добавить кабинет</b> — добавить новый кабинет\n"
        "➕ <b>Добавить объект</b> — добавить объект в кабинет (можно указать модель, производителя, серийный номер)\n"
        "👀 <b>Посмотреть содержимое</b> — просмотреть все объекты в выбранном кабинете с подробной информацией\n"
        "🔍 <b>Расширенный поиск</b> — найти объекты по названию, модели, производителю или серийному номеру\n"
        "🗑️ <b>Удалить объект</b> — удалить выбранный объект из кабинета\n"
        "⛔ <b>Удалить кабинет</b> — удалить кабинет (только если в нём нет объектов)\n\n"
        "Начните с добавления кабинета через «📦 Добавить кабинет»!"
    )
    bot.send_message(message.chat.id, help_text, parse_mode='HTML', reply_markup=main_menu())

@bot.message_handler(commands=['add_cabinet'])
def add_cabinet(message):
    msg = bot.send_message(message.chat.id, "Введите номер кабинета:")
    bot.register_next_step_handler(msg, process_cabinet_number)

def process_cabinet_number(message):
    number = message.text.strip()
    if not number:
        bot.send_message(message.chat.id, "Номер кабинета не может быть пустым!")
        start(message)
        return

    conn = sqlite3.connect('inventory.db')
    try:
        conn.execute("INSERT INTO cabinets (number) VALUES (?)", (number,))
        conn.commit()
        bot.send_message(message.chat.id, f"Кабинет {number} добавлен!")
    except sqlite3.IntegrityError:
        bot.send_message(message.chat.id, f"Кабинет {number} уже существует!")
    finally:
        conn.close()
    start(message)
@bot.message_handler(func=lambda message: message.text == "➕ Добавить объект")
@bot.message_handler(commands=['add_item'])
def add_item(message):
    conn = sqlite3.connect('inventory.db')
    cabinets = conn.execute("SELECT number FROM cabinets ORDER BY number").fetchall()
    conn.close()

    if not cabinets:
        bot.send_message(message.chat.id, "Нет кабинетов! Добавьте кабинет через '📦 Добавить кабинет'")
        start(message)
        return

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for (number,) in cabinets:
        markup.add(number)

    msg = bot.send_message(message.chat.id, "Выберите кабинет:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_item_cabinet)



def process_item_cabinet(message):
    cabinet_number = message.text.strip()

    conn = sqlite3.connect('inventory.db')
    cabinet = conn.execute("SELECT id FROM cabinets WHERE number = ?", (cabinet_number,)).fetchone()
    conn.close()

    if not cabinet:
        bot.send_message(message.chat.id, "Кабинет не найден! Попробуйте ещё раз.")
        start(message)
        return

    cabinet_id = cabinet[0]
    markup=types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("🔎 Использовать фильтр")
    markup.add("➕ Без фильтра")
    msg = bot.send_message(message.chat.id, "Хотите использовать фильтр для добавления объекта?", reply_markup=markup)
    bot.register_next_step_handler(msg, process_filter_choice, cabinet_id)

def process_filter_choice(message, cabinet_id):
    choice = message.text

    if choice == "🔎 Использовать фильтр":
        show_filter_menu(message, cabinet_id)
    elif choice == "➕ Без фильтра":
        msg = bot.send_message(message.chat.id, "Название объекта:")
        bot.register_next_step_handler(msg, process_item_name, cabinet_id)
    else:
        # Если пользователь ввёл что‑то иное, возвращаем к выбору
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add("🔎 Использовать фильтр")
        markup.add("➕ Без фильтра")
        msg = bot.send_message(
            message.chat.id,
            "Пожалуйста, выберите вариант:",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_filter_choice, cabinet_id)

def show_filter_menu(message, cabinet_id):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    btn1 = types.KeyboardButton("🏷️ По модели")
    btn2 = types.KeyboardButton("🏭 По производителю")
    btn3 = types.KeyboardButton("🆔 По серийному номеру")
    btn4 = types.KeyboardButton("🔙 Назад")
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)

    msg = bot.send_message(message.chat.id,"Выберите тип фильтра:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_filter_type, cabinet_id)

def process_filter_type(message, cabinet_id):
    filter_type = message.text

    if filter_type == "🔙 Назад":
        start(message)
        return

    filter_mapping = {
        "🏷️ По модели": "model",
        "🏭 По производителю": "manufacturer",
        "🆔 По серийному номеру": "serial_number"
    }

    field = filter_mapping.get(filter_type)
    if not field:
        start(message)
        return

    msg = bot.send_message(message.chat.id,f"Введите значение для фильтра {filter_type.lower()}:")
    bot.register_next_step_handler(msg, apply_filter, cabinet_id, field)
def apply_filter(message, cabinet_id, field):
    query = message.text.strip()
    if not query:
        bot.send_message(message.chat.id, "Запрос не может быть пустым!")
        show_filter_menu(message, cabinet_id)
        return

    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()

    cursor.execute(f'''
        SELECT DISTINCT {field}
        FROM items
        WHERE cabinet_id = ? AND {field} IS NOT NULL AND LOWER({field}) LIKE LOWER(?)
    ''', (cabinet_id, f'%{query}%'))

    results = cursor.fetchall()
    conn.close()

    if not results:
        bot.send_message(
            message.chat.id,
            f"По фильтру ничего не найдено. Добавим новый объект."
        )
        msg = bot.send_message(message.chat.id, "Название объекта:")
        bot.register_next_step_handler(msg, process_item_name, cabinet_id)
        return

    # Формируем клавиатуру с найденными значениями
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for (value,) in results:
        markup.add(value)
    markup.add("➕ Новый объект")

    msg = bot.send_message(
        message.chat.id,
        f"Выберите значение из списка или добавьте новое:",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_filtered_value, cabinet_id, field)

def process_filtered_value(message, cabinet_id, field):
    selected_value = message.text

    if selected_value == "➕ Новый объект":
        msg = bot.send_message(message.chat.id, "Название объекта:")
        bot.register_next_step_handler(msg, process_item_name, cabinet_id)
        return

    # Сохраняем выбранное значение как основу для нового объекта
    initial_data = {field: selected_value}

    # Сразу переходим к вводу названия — остальные поля заполним позже
    msg = bot.send_message(message.chat.id, "Название объекта:")
    bot.register_next_step_handler(
        msg,
        process_item_name_with_filter,
        cabinet_id,
        initial_data
    )
def process_item_name_with_filter(message, cabinet_id, initial_data):
    name = message.text.strip()
    if not name:
        bot.send_message(message.chat.id, "Название не может быть пустым!")
        start(message)
        return

    model = initial_data.get('model')
    manufacturer = initial_data.get('manufacturer')
    serial = initial_data.get('serial_number')

    msg = bot.send_message(message.chat.id, "Количество (число):")
    bot.register_next_step_handler(
        msg,
        process_quantity_with_filter,
        cabinet_id,
        name,
        model,
        manufacturer,
        serial
    )

def process_quantity_with_filter(message, cabinet_id, name, model, manufacturer, serial):
    try:
        quantity = int(message.text)
        if quantity <= 0:
            bot.send_message(message.chat.id, "Количество должно быть > 0!")
            start(message)
            return
    except ValueError:
        bot.send_message(message.chat.id, "Введите число!")
        start(message)
        return

    # Если какие‑то поля уже заполнены фильтром, предлагаем их отредактировать
    prompt_fields = []
    if model is None:
        prompt_fields.append('model')
    if manufacturer is None:
        prompt_fields.append('manufacturer')
    if serial is None:
        prompt_fields.append('serial_number')

    if prompt_fields:
        # Запрашиваем оставшиеся поля
        ask_next_field(
            message,
            cabinet_id,
            name,
            quantity,
            model,
            manufacturer,
            serial,
            prompt_fields
        )
    else:
        # Все поля заполнены — запрашиваем описание
        ask_description(
            message,
            cabinet_id,
            name,
            quantity,
            model,
            manufacturer,
            serial
        )

def ask_next_field(message, cabinet_id, name, quantity, model, manufacturer, serial, remaining_fields):
    if not remaining_fields:
        # Все поля заполнены — сразу переходим к описанию
        ask_description(
            message,
            cabinet_id,
            name,
            quantity,
            model,
            manufacturer,
            serial
        )
        return

    field = remaining_fields[0]
    remaining_fields = remaining_fields[1:]

    field_names = {
        'model': 'модель',
        'manufacturer': 'производитель',
        'serial_number': 'серийный номер'
    }

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("Пропустить")

    msg = bot.send_message(
        message.chat.id,
        f"Укажите {field_names[field]} (или нажмите «Пропустить»):",
        reply_markup=markup
    )
    bot.register_next_step_handler(
        msg,
        process_next_field,
        cabinet_id,
        name,
        quantity,
        model,
        manufacturer,
        serial,
        remaining_fields,
        field
    )
def process_next_field(message, cabinet_id, name, quantity, model, manufacturer, serial, remaining_fields, current_field):
    user_input = message.text.strip()

    # Обновляем соответствующие поля
    if user_input.lower() == "пропустить" or not user_input:
        new_model = model
        new_manufacturer = manufacturer
        new_serial = serial
    else:
        if current_field == 'model':
            new_model = user_input
            new_manufacturer = manufacturer
            new_serial = serial
        elif current_field == 'manufacturer':
            new_model = model
            new_manufacturer = user_input
            new_serial = serial
        else:  # serial_number
            new_model = model
            new_manufacturer = manufacturer
            new_serial = user_input

    # Переходим к следующему полю или к описанию
    ask_next_field(
        message,
        cabinet_id,
        name,
        quantity,
        new_model,
        new_manufacturer,
        new_serial,
        remaining_fields
    )
def ask_description(message, cabinet_id, name, quantity, model, manufacturer, serial):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("Пропустить")

    msg = bot.send_message(
        message.chat.id,
        "Описание (опционально). Нажмите «Пропустить», чтобы не указывать:",
        reply_markup=markup
    )
    bot.register_next_step_handler(
        msg,
        save_item_with_filters,
        cabinet_id,
        name,
        quantity,
        model,
        manufacturer,
        serial
    )

def save_item_with_filters(message, cabinet_id, name, quantity, model, manufacturer, serial):
    user_input = message.text.strip()

    if user_input.lower() == "пропустить" or not user_input:
        description = "Нет описания"
    else:
        description = user_input

    conn = sqlite3.connect('inventory.db')
    conn.execute(
        "INSERT INTO items (cabinet_id, name, quantity, description, model, manufacturer, serial_number) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (cabinet_id, name, quantity, description, model, manufacturer, serial)
    )
    conn.commit()
    conn.close()

    # Формируем сообщение с карточкой добавленного объекта
    card = f"✅ <b>Объект успешно добавлен!</b>\n\n"
    card += f"📦 <b>{name}</b>\n"
    card += f"🔢 Количество: <b>{quantity} шт.</b>\n"

    if model:
        card += f"🏷️ Модель: <code>{model}</code>\n"
    if manufacturer:
        card += f"🏭 Производитель: <b>{manufacturer}</b>\n"
    if serial:
        card += f"🆔 Серийный номер: <code>{serial}</code>\n"
    if description and description != "Нет описания":
        card += f"📝 Описание: <i>{description}</i>\n"

    bot.send_message(message.chat.id, card, parse_mode='HTML')
    start(message)
def process_item_name(message, cabinet_id):
    name = message.text.strip()
    if not name:
        bot.send_message(message.chat.id, "Название не может быть пустым!")
        start(message)
        return

    msg = bot.send_message(message.chat.id, "Количество (число):")
    bot.register_next_step_handler(msg, process_quantity, cabinet_id, name)



def process_quantity(message, cabinet_id, name):
    try:
        quantity = int(message.text)
        if quantity <= 0:
            bot.send_message(message.chat.id, "Количество должно быть > 0!")
            start(message)
            return
    except ValueError:
        bot.send_message(message.chat.id, "Введите число!")
        start(message)
        return

    # Создаём клавиатуру с вариантом "Пропустить"
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("Пропустить")

    msg = bot.send_message(
        message.chat.id,
        "Описание (опционально). Нажмите «Пропустить», чтобы не указывать:",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_description, cabinet_id, name, quantity)



def process_description(message, cabinet_id, name, quantity):
    user_input = message.text.strip()

    if user_input.lower() == "пропустить" or not user_input:
        description = "Нет описания"
    else:
        description = user_input

    conn = sqlite3.connect('inventory.db')
    conn.execute(
        "INSERT INTO items (cabinet_id, name, quantity, description) VALUES (?, ?, ?, ?)",
        (cabinet_id, name, quantity, description)
    )
    conn.commit()
    conn.close()

    bot.send_message(message.chat.id, f"Объект '{name}' добавлен в кабинет!")
    start(message)

@bot.message_handler(func=lambda message: message.text == "👀 Посмотреть содержимое")
@bot.message_handler(commands=['view'])
def view_cabinet(message):
    conn = sqlite3.connect('inventory.db')
    cabinets = conn.execute("SELECT number FROM cabinets ORDER BY number").fetchall()
    conn.close()

    if not cabinets:
        bot.send_message(message.chat.id, "Нет кабинетов! Добавьте кабинет через «📦 Добавить кабинет»")
        return

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for (number,) in cabinets:
        markup.add(number)

    msg = bot.send_message(
        message.chat.id,
        "Выберите кабинет для просмотра:",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_view_cabinet)

def process_view_cabinet(message):
    cabinet_number = message.text.strip()

    conn = sqlite3.connect('inventory.db')
    cabinet = conn.execute("SELECT id FROM cabinets WHERE number = ?", (cabinet_number,)).fetchone()

    if not cabinet:
        bot.send_message(message.chat.id, f"Кабинет {cabinet_number} не найден!")
        conn.close()
        start(message)
        return

    items = conn.execute('''SELECT name, quantity, description, model, manufacturer, serial_number
                          FROM items
                          WHERE cabinet_id = ?
                          ORDER BY name''', (cabinet[0],)).fetchall()
    conn.close()

    if not items:
        bot.send_message(message.chat.id, f"В кабинете {cabinet_number} нет объектов!")
        start(message)
        return

    # Отправляем карточки предметов
    for name, qty, desc, model, manufacturer, serial in items:
        card = f"📦 <b>{name}</b>\n"
        card += f"🔢 Количество: <b>{qty} шт.</b>\n"

        if model:
            card += f"🏷️ Модель: <code>{model}</code>\n"
        if manufacturer:
            card += f"🏭 Производитель: <b>{manufacturer}</b>\n"
        if serial:
            card += f"🆔 Серийный номер: <code>{serial}</code>\n"
        if desc and desc != "Нет описания":
            card += f"📝 Описание: <i>{desc}</i>\n"

        bot.send_message(message.chat.id, card, parse_mode='HTML')

    start(message)

@bot.message_handler(commands=['search'])
def search(message):
    msg = bot.send_message(message.chat.id, "Введите название объекта для поиска:")
    bot.register_next_step_handler(msg, process_search_query)


def process_search_query(message):
    query = message.text.strip()
    if not query:
        bot.send_message(message.chat.id, "Запрос не может быть пустым!")
        start(message)
        return

    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT c.number, i.name, i.quantity, i.description
        FROM items i
        JOIN cabinets c ON i.cabinet_id = c.id
        WHERE LOWER(i.name) LIKE LOWER(?)
        ORDER BY c.number, i.name
    ''', (f'%{query}%',))

    results = cursor.fetchall()
    conn.close()

    if not results:
        bot.send_message(message.chat.id, f"Ничего не найдено по запросу «{query}».")
    else:
        response = f"Результаты поиска по запросу «{query}»:\n\n"
        for cabinet_num, name, qty, desc in results:
            response += (
                f"Кабинет {cabinet_num}:\n"
                f"  • {name} ({qty} шт.)\n"
                f"    • {desc}\n\n"
            )
        bot.send_message(message.chat.id, response)

    start(message)
@bot.message_handler(func=lambda message: message.text == "🔍 Расширенный поиск")
@bot.message_handler(commands=['search_advanced'])
def advanced_search(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    btn1 = types.KeyboardButton("🔎 По названию")
    btn2 = types.KeyboardButton("🏭 По производителю")
    btn3 = types.KeyboardButton("🏷️ По модели")
    btn4 = types.KeyboardButton("🆔 По серийному номеру")
    btn5 = types.KeyboardButton("🔙 Назад")
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5)

    msg = bot.send_message(
        message.chat.id,
        "Выберите тип поиска:",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_search_type)

def process_search_type(message):
    search_type = message.text

    if search_type == "🔙 Назад":
        start(message)
        return

    search_mapping = {
        "🔎 По названию": "name",
        "🏭 По производителю": "manufacturer",
        "🏷️ По модели": "model",
        "🆔 По серийному номеру": "serial_number"
    }

    if search_type not in search_mapping:
        start(message)
        return

    field = search_mapping[search_type]
    msg = bot.send_message(
        message.chat.id,
        f"Введите запрос для поиска по {search_type.lower()}:"
    )
    bot.register_next_step_handler(msg, process_advanced_search, field)

def process_advanced_search(message, field):
    query = message.text.strip()
    if not query:
        bot.send_message(message.chat.id, "Запрос не может быть пустым!")
        advanced_search(message)
        return

    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()

    cursor.execute(f'''
        SELECT c.number, i.name, i.quantity, i.description, i.model, i.manufacturer, i.serial_number
        FROM items i
        JOIN cabinets c ON i.cabinet_id = c.id
        WHERE LOWER(i.{field}) LIKE LOWER(?)
        ORDER BY c.number, i.name
    ''', (f'%{query}%',))

    results = cursor.fetchall()
    conn.close()

    if not results:
        bot.send_message(message.chat.id, f"Ничего не найдено по запросу «{query}».")
    else:
        response = f"🔍 Результаты поиска по запросу «{query}»:\n\n"
        for cabinet_num, name, qty, desc, model, manufacturer, serial in results:
            response += f"📍 Кабинет {cabinet_num}:\n"
            response += f"  📦 <b>{name}</b> ({qty} шт.)\n"

            if model:
                response += f"  🏷️ <i>{model}</i>\n"
            if manufacturer:
                response += f"  🏭 <i>{manufacturer}</i>\n"
            if serial:
                response += f"  🆔 <code>{serial}</code>\n"
            if desc and desc != "Нет описания":
                response += f"  📝 <i>{desc}</i>\n\n"
            response = f"🔍 Результаты поиска по запросу «{query}»:\n\n"
            for cabinet_num, name, qty, desc, model, manufacturer, serial in results:
                response += f"📍 Кабинет {cabinet_num}:\n"
                response += f"  📦 <b>{name}</b> ({qty} шт.)\n"

                if model:
                    response += f"  🏷️ <i>{model}</i>\n"
                if manufacturer:
                    response += f"  🏭 <i>{manufacturer}</i>\n"
                if serial:
                    response += f"  🆔 <code>{serial}</code>\n"
                if desc and desc != "Нет описания":
                    response += f"  📝 <i>{desc}</i>\n\n"

            bot.send_message(message.chat.id, response, parse_mode='HTML')
            start(message)

@bot.message_handler(commands=['delete'])
def delete(message):
    conn = sqlite3.connect('inventory.db')
    cabinets = conn.execute("SELECT number FROM cabinets ORDER BY number").fetchall()
    conn.close()

    if not cabinets:
        bot.send_message(message.chat.id, "Нет кабинетов! Ничего удалять.")
        start(message)
        return

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for (number,) in cabinets:
        markup.add(number)

    msg = bot.send_message(message.chat.id, "Выберите кабинет для удаления объекта:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_delete_cabinet)

def process_delete_cabinet(message):
    cabinet_number = message.text.strip()

    conn = sqlite3.connect('inventory.db')
    cabinet = conn.execute("SELECT id FROM cabinets WHERE number = ?", (cabinet_number,)).fetchone()

    if not cabinet:
        bot.send_message(message.chat.id, "Кабинет не найден! Попробуйте ещё раз.")
        conn.close()
        start(message)
        return

    cabinet_id = cabinet[0]
    items = conn.execute(
        "SELECT id, name, quantity FROM items WHERE cabinet_id = ?",
        (cabinet_id,)
    ).fetchall()
    conn.close()

    if not items:
        bot.send_message(message.chat.id, f"В кабинете {cabinet_number} нет объектов для удаления.")
        start(message)
        return

    # Формируем клавиатуру с названиями объектов
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for item_id, name, qty in items:
        markup.add(f"{name} ({qty} шт.)")

    msg = bot.send_message(
        message.chat.id,
        f"Выберите объект для удаления из кабинета {cabinet_number}:",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_delete_item, cabinet_id)

def process_delete_item(message, cabinet_id):
    user_input = message.text.strip()

    # Извлекаем название (убираем количество в скобках)
    item_name = user_input.split(' (')[0]

    conn = sqlite3.connect('inventory.db')
    # Ищем объект по названию и кабинету
    item = conn.execute(
        "SELECT id FROM items WHERE cabinet_id = ? AND name = ?",
        (cabinet_id, item_name)
    ).fetchone()

    if not item:
        bot.send_message(message.chat.id, "Объект не найден! Попробуйте снова.")
        conn.close()
        start(message)
        return

    item_id = item[0]

    # Спрашиваем подтверждение
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add("Да")
    markup.add("Нет")

    msg = bot.send_message(
        message.chat.id,
        f"Вы уверены, что хотите удалить объект «{item_name}»?",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, confirm_delete, item_id, item_name)
    conn.close()

def confirm_delete(message, item_id, item_name):
    answer = message.text.strip().lower()

    if answer not in ['да', 'нет']:
        bot.send_message(message.chat.id, "Пожалуйста, выберите «Да» или «Нет».")
        start(message)
        return

    if answer == 'да':
        conn = sqlite3.connect('inventory.db')
        conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"Объект «{item_name}» удалён.")
    else:
        bot.send_message(message.chat.id, "Удаление отменено.")

    start(message)  # Возврат к стартовому меню

@bot.message_handler(commands=['delete_cabinet'])
def delete_cabinet(message):
    conn = sqlite3.connect('inventory.db')
    cabinets = conn.execute("SELECT number FROM cabinets ORDER BY number").fetchall()
    conn.close()

    if not cabinets:
        bot.send_message(message.chat.id, "Нет кабинетов для удаления.")
        start(message)
        return

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for (number,) in cabinets:
        markup.add(number)

    msg = bot.send_message(message.chat.id, "Выберите кабинет для удаления:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_delete_cabinet_confirm)


def process_delete_cabinet_confirm(message):
    cabinet_number = message.text.strip()

    conn = sqlite3.connect('inventory.db')

    # Находим ID кабинета
    cabinet = conn.execute(
        "SELECT id FROM cabinets WHERE number = ?", (cabinet_number,)
    ).fetchone()

    if not cabinet:
        bot.send_message(message.chat.id, f"Кабинет {cabinet_number} не найден!")
        conn.close()
        start(message)
        return

    cabinet_id = cabinet[0]

    # Проверяем, есть ли объекты в кабинете
    item_count = conn.execute(
        "SELECT COUNT(*) FROM items WHERE cabinet_id = ?", (cabinet_id,)
    ).fetchone()[0]

    if item_count > 0:
        bot.send_message(
            message.chat.id,
            f"В кабинете {cabinet_number} есть {item_count} объектов!\n"
            "Удалите их через /delete, затем повторите попытку."
        )
        conn.close()
        start(message)
        return

    # Если объектов нет — запрашиваем подтверждение
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add("Да")
    markup.add("Нет")

    msg = bot.send_message(
        message.chat.id,
        f"Вы уверены, что хотите удалить кабинет {cabinet_number}?",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, confirm_delete_cabinet, cabinet_id, cabinet_number)
    conn.close()

def confirm_delete_cabinet(message, cabinet_id, cabinet_number):
    answer = message.text.strip().lower()

    if answer not in ['да', 'нет']:
        bot.send_message(message.chat.id, "Пожалуйста, выберите «Да» или «Нет».")
        start(message)
        return

    if answer == 'да':
        conn = sqlite3.connect('inventory.db')
        try:
            conn.execute("DELETE FROM cabinets WHERE id = ?", (cabinet_id,))
            conn.commit()
            bot.send_message(message.chat.id, f"Кабинет {cabinet_number} удалён.")
        except sqlite3.Error as e:
            bot.send_message(message.chat.id, f"Ошибка при удалении: {e}")
        finally:
            conn.close()
    else:
        bot.send_message(message.chat.id, "Удаление кабинета отменено.")

    start(message)  # Возврат к стартовому меню

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    text = message.text

    if text == "📦 Добавить кабинет":
        add_cabinet(message)
    elif text == "➕ Добавить объект":
        add_item(message)
    elif text == "👀 Посмотреть содержимое":
        view_cabinet(message)
    elif text == "🔍 Расширенный поиск":
        advanced_search(message)
    elif text == "🗑️ Удалить объект":
        delete(message)
    elif text == "⛔ Удалить кабинет":
        delete_cabinet(message)
    elif text == "ℹ️ Справка":
        help(message)
    else:
        bot.send_message(
            message.chat.id,
            "Неизвестная команда. Используйте кнопки меню или /start для главного меню.",
            reply_markup=main_menu()
        )
if __name__ == '__main__':
    init_db()
    bot.polling()

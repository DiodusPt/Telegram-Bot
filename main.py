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
                 FOREIGN KEY (cabinet_id) REFERENCES cabinets (id))''')
    conn.commit()
    conn.close()

@bot.message_handler(commands=['start'])
def start(message):
    user_first_name = message.from_user.first_name
    bot.send_message(message.chat.id, f"Приветствую, {user_first_name}! Я бот-инвентаризатор и я помогу Вам вести инвентарный учёт Вашей организации!\n\n"
                                      "Доступные команды: \n"
                                      "1. /add_cabinet — добавить кабинет;\n"
                                      "2. /add_item — добавить объект в кабинет; \n"
                                      "3. /view — посмотреть содержимое кабинета; \n"
                                      "4. /search — найти объект по названию; \n"
                                      "5. /help — справка.")

@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, "1. Добавьте кабинет через /add_cabinet\n"
                                      "2. Добавьте объекты через /add_item\n"
                                      "3. Посмотрите содержимое кабинета через /view <номер кабинета>\n"
                                      "4. Найдите объект через /search\n")
    start(message)

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

@bot.message_handler(commands=['add_item'])
def add_item(message):
    conn = sqlite3.connect('inventory.db')
    cabinets = conn.execute("SELECT number FROM cabinets ORDER BY number").fetchall()
    conn.close()

    if not cabinets:
        bot.send_message(message.chat.id, "Нет кабинетов! Добавьте кабинет через /add_cabinet")
        start(message)
        return

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
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
    msg = bot.send_message(message.chat.id, "Название объекта:")
    bot.register_next_step_handler(msg, process_item_name, cabinet_id)



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

@bot.message_handler(commands=['view'])
def view_cabinet(message):
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(message.chat.id, "Используйте: /view <номер кабинета>")
        start(message)
        return

    cabinet_number = args[1]

    conn = sqlite3.connect('inventory.db')
    cabinet = conn.execute("SELECT id FROM cabinets WHERE number = ?", (cabinet_number,)).fetchone()

    if not cabinet:
        bot.send_message(message.chat.id, f"Кабинет {cabinet_number} не найден!")
        conn.close()
        start(message)
        return

    items = conn.execute('''SELECT name, quantity, description FROM items 
                              WHERE cabinet_id = ? ORDER BY name''', (cabinet[0],)).fetchall()
    conn.close()

    if not items:
        bot.send_message(message.chat.id, f"В кабинете {cabinet_number} нет объектов!")
        start(message)
        return

    response = f"Содержимое кабинета {cabinet_number}:\n\n"
    for name, qty, desc in items:
        response += f"• {name} ({qty} шт.)\n  • {desc}\n\n"

    bot.send_message(message.chat.id, response)
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

if __name__ == '__main__':
    init_db()
    bot.polling()

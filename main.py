import sqlite3
import telebot
from config import TOKEN

bot = telebot.TeleBot(TOKEN)


def proverka_bd():
    try:
        with sqlite3.connect('Users.db') as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS users (
                UserId TEXT PRIMARY KEY,
                firstname TEXT,
                lastname TEXT,
                UserName TEXT
            )''')
            conn.commit()
    except Exception as e:
        print(f"Ошибка при создании таблицы: {e}")


@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)

    # Проверка регистрации пользователя
    with sqlite3.connect('Users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE UserId = ?", (user_id,))
        user = cursor.fetchone()

    if user:
        bot.send_message(message.chat.id, "Вы уже зарегистрированы!")
    else:
        # Автоматическая регистрация при /start
        with sqlite3.connect('Users.db') as conn:
            conn.execute(
                "INSERT INTO users (UserId, firstname, lastname, UserName) VALUES (?, ?, ?, ?)",
                (
                    user_id,
                    message.from_user.first_name or "",
                    message.from_user.last_name or "",
                    message.from_user.username or ""
                )
            )
            conn.commit()
        bot.send_message(message.chat.id, "Вы успешно зарегистрированы!")

    bot.send_message(
        message.chat.id,
        "Используйте /register для обновления данных\n"
        "или /check для проверки регистрации"
    )


@bot.message_handler(commands=['register'])
def register(message):
    bot.send_message(message.chat.id, "Введите ваше имя:")
    bot.register_next_step_handler(message, process_firstname)


def process_firstname(message):
    firstname = str(message.text.strip())

    if not firstname:
        bot.send_message(message.chat.id, "Имя не может быть пустым. Попробуйте снова:")
        bot.register_next_step_handler(message, process_firstname, )
        return

    bot.send_message(message.chat.id, "Введите вашу фамилию:")
    bot.register_next_step_handler(message, process_lastname,firstname)


def process_lastname(message, firstname):
    lastname = (message.text.strip())

    if not lastname:
        bot.send_message(message.chat.id, "Фамилия не может быть пустой. Попробуйте снова:")
        bot.register_next_step_handler(message, process_lastname,firstname)
        return

    username = message.from_user.username or ""

    # Сохраняем данные в БД
    try:
        with sqlite3.connect('Users.db') as conn:
            user_id = message.from_user.id
            conn.execute(
                "UPDATE Users SET firstname = ?, lastname = ? WHERE UserId = ?",
                (firstname, lastname, user_id,)
            )
            conn.commit()

        bot.send_message(message.chat.id, "Данные успешно обновлены!")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка сохранения: {e}")


@bot.message_handler(commands=['check'])
def check_registration(message):
    user_id = str(message.from_user.id)

    with sqlite3.connect('Users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT firstname, lastname, UserName FROM users WHERE UserId = ?", (user_id,))
        user = cursor.fetchone()

    if user:
        response = (
            f"Ваши данные:\n"
            f"Имя: {user[0] or 'не указано'}\n"
            f"Фамилия: {user[1] or 'не указано'}\n"
            f"Username: {user[2] or 'не указано'}"
        )
        bot.send_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, "Вы не зарегистрированы. Используйте /start или /register.")


if __name__ == '__main__':
    proverka_bd()
    bot.polling(none_stop=True)
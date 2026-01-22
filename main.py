import sqlite3
import sys

import telebot
import logging
from config import TOKEN

bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('bot.log', encoding="utf-8")])
logger = logging.getLogger(__name__)


@bot.message_handler(commands=['help'])
def command_help(message):
    logger.info(f"User {message.from_user.id} selected /help. ")
    bot.send_message(message.chat.id,text="/start - launching the bot. \n"
                                          "/register - updating user data. \n"
                                          "/check - checking how the user is logged into the database.\n"
                     )
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
            logger.info(f"Database created/checked successfully")
    except Exception as e:
        logger.info(f"Database error: {e}")


@bot.message_handler(commands=['start'])
def start(message):
    logger.info(f"User {message.from_user.id} selected /start. ")
    user_id = str(message.from_user.id)

    with sqlite3.connect('Users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE UserId = ?", (user_id,))
        user = cursor.fetchone()

    if user:
        bot.send_message(message.chat.id, "You are already registered!")
    else:
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
        logger.info(f"User {message.from_user.id} registered successfully")
        bot.send_message(message.chat.id, "You are already registered!")

    bot.send_message(
        message.chat.id,
        "Use /register for update data\n"
        "or /check to verify registration"
    )


@bot.message_handler(commands=['register'])
def register(message):
    logger.info(f"User {message.from_user.id} selected /register. ")
    bot.send_message(message.chat.id, "Enter your name:")

    bot.register_next_step_handler(message, process_firstname)


def process_firstname(message):
    firstname = str(message.text.strip())
    logger.info(f"User {message.from_user.id} enter his name")
    if not firstname:
        bot.send_message(message.chat.id, "Name can't be empty. Try again:")
        bot.register_next_step_handler(message, process_firstname, )
        return

    bot.send_message(message.chat.id, "Enter your lastname:")
    bot.register_next_step_handler(message, process_lastname,firstname)


def process_lastname(message, firstname):
    lastname = (message.text.strip())
    logger.info(f"User {message.from_user.id} enter his lastname")
    if not lastname:
        bot.send_message(message.chat.id, "Lastname can't be empty. Try again:")
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

        bot.send_message(message.chat.id, "Data was updated successfully!")
        logger.info(f"User's data updated successfully")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error of saving: {e}")


@bot.message_handler(commands=['check'])
def check_registration(message):
    user_id = str(message.from_user.id)
    logger.info(f"User {message.from_user.id} selected /check.")
    with sqlite3.connect('Users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT firstname, lastname, UserName FROM users WHERE UserId = ?", (user_id,))
        user = cursor.fetchone()

    if user:
        response = (
            f"Your data:\n"
            f"Name: {user[0] or 'empty'}\n"
            f"Lastname: {user[1] or 'empty'}\n"
            f"Username: {user[2] or 'empty'}"
        )
        bot.send_message(message.chat.id, response)
        logger.info(f"User's data was printed.")
    else:
        bot.send_message(message.chat.id, "You are not registered. Use /start or /register.")
        logger.info(f"User {message.from_user.id} not registered.")

if __name__ == '__main__':
    proverka_bd()
    bot.polling(none_stop=True)

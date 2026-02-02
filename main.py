import sqlite3
import telebot
import logging
from config import TOKEN

ADMIN_ID=[1076758130]
bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('bot.log', encoding="utf-8")])
logger = logging.getLogger(__name__)

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
            conn.execute('''CREATE TABLE IF NOT EXISTS banned_users (
                            UserId TEXT PRIMARY KEY
                        )''')
            conn.commit()
            logger.info(f"Database created/checked successfully")
    except Exception as e:
        logger.info(f"Database error: {e}")

def is_banned(user_id):
    with sqlite3.connect('Users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM banned_users WHERE UserId = ?", (str(user_id),))
        return cursor.fetchone() is not None

def check_ban_and_notify(message):
    if is_banned(message.from_user.id):
        bot.send_message(message.chat.id, "❌ You are banned and cannot use this bot.")
        logger.warning(f"Blocked message from banned user {message.from_user.id}")
        return True
    return False

@bot.message_handler(commands=['help'])
def command_help(message):
    logger.info(f"User {message.from_user.id} selected /help. ")
    bot.send_message(message.chat.id,text="/start - launching the bot. \n"
                                          "/register - updating user data. \n"
                                          "/check - checking how the user is logged into the database.\n")

@bot.message_handler(commands=['help_adm'])
def command_help_adm(message):
    if message.from_user.id in ADMIN_ID:
        logger.info(f"Adm {message.from_user.id} selected /help_adm.")
        bot.send_message(message.chat.id,text="/users_list - list of all users (admin only). \n"
                                            "/ban <id> - ban user (admin only). \n"
                                            "/unban <id> - unban user (admin only).")



@bot.message_handler(commands=['start'])
def start(message):
    if check_ban_and_notify(message):
        return
    logger.info(f"User {message.from_user.id} selected /start. ")
    user_id = str(message.from_user.id)
    with sqlite3.connect('Users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM banned_users WHERE UserId = ?", (user_id,))
        if cursor.fetchone():
            bot.send_message(message.chat.id, "You are banned.")
            return

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
    if check_ban_and_notify(message):
        return
    logger.info(f"User {message.from_user.id} selected /register. ")
    bot.send_message(message.chat.id, "Enter your name:")

    bot.register_next_step_handler(message, process_firstname)


def process_firstname(message):
    if check_ban_and_notify(message):
        return
    firstname = str(message.text.strip())
    logger.info(f"User {message.from_user.id} enter his name")
    if not firstname:
        bot.send_message(message.chat.id, "Name can't be empty. Try again:")
        bot.register_next_step_handler(message, process_firstname, )
        return

    bot.send_message(message.chat.id, "Enter your lastname:")
    bot.register_next_step_handler(message, process_lastname,firstname)


def process_lastname(message, firstname):
    if check_ban_and_notify(message):
        return
    lastname = (message.text.strip())
    logger.info(f"User {message.from_user.id} enter his lastname")
    if not lastname:
        bot.send_message(message.chat.id, "Lastname can't be empty. Try again:")
        bot.register_next_step_handler(message, process_lastname,firstname)
        return

    username = message.from_user.username or ""

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
    if check_ban_and_notify(message):
        return
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

@bot.message_handler(commands=['users_list'])
def users_list(message):
    if message.from_user.id not in ADMIN_ID:
        bot.send_message(message.chat.id, "Access denied.")
        logger.warning(f"User {message.from_user.id} tried to access /users_list without permission.")
        return

    logger.info(f"Admin {message.from_user.id} requested /users_list.")
    with sqlite3.connect('Users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT UserId, firstname, lastname, UserName FROM users")
        users = cursor.fetchall()

    if users:
        response = "📋 Registered users:\n\n"
        for i, user in enumerate(users, 1):
            user_id, firstname, lastname, username = user
            username_str = f"@{username}" if username else "not set"
            response += (f"{i}. ID: <code>{user_id}</code>\n"
                     f"   Name: {firstname} {lastname}\n"
                     f"   Username: {username_str}\n")
        bot.send_message(message.chat.id, response, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, "No users found in the database.")
    logger.info(f"Admin {message.from_user.id} received users list.")



@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id not in ADMIN_ID:
        bot.send_message(message.chat.id, "Access denied.")
        logger.warning(f"User {message.from_user.id} tried to use /ban without permission.")
        return

    args = message.text.split()
    if len(args) != 2:
        bot.send_message(message.chat.id, "Usage: /ban <user_id>")
        return

    try:
        user_id_to_ban = str(int(args[1]))  # Преобразуем в int, потом в str для единообразия
    except ValueError:
        bot.send_message(message.chat.id, "User ID must be a number.")
        return

    with sqlite3.connect('Users.db') as conn:
        cursor = conn.cursor()

        # Проверяем, есть ли пользователь в users
        cursor.execute("SELECT 1 FROM users WHERE UserId = ?", (user_id_to_ban,))
        if not cursor.fetchone():
            bot.send_message(message.chat.id, f"User {user_id_to_ban} is not registered.")
            logger.info(f"Attempt to ban non-registered user {user_id_to_ban}.")
            return

        cursor.execute("SELECT 1 FROM banned_users WHERE UserId = ?", (user_id_to_ban,))
        if cursor.fetchone():
            bot.send_message(message.chat.id, f"User {user_id_to_ban} is already banned.")
            logger.info(f"User {user_id_to_ban} was already banned.")
            return

        # Баним
        conn.execute("INSERT INTO banned_users (UserId) VALUES (?)", (user_id_to_ban,))
        conn.commit()

    bot.send_message(message.chat.id, f"✅ User {user_id_to_ban} has been banned.")
    logger.info(f"Admin {message.from_user.id} banned user {user_id_to_ban}.")


@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id not in ADMIN_ID:
        bot.send_message(message.chat.id, "Access denied.")
        logger.warning(f"User {message.from_user.id} tried to use /unban without permission.")
        return

    args = message.text.split()
    if len(args) != 2:
        bot.send_message(message.chat.id, "Usage: /unban <user_id>")
        return

    try:
        user_id_to_unban = str(int(args[1]))
    except ValueError:
        bot.send_message(message.chat.id, "User ID must be a number.")
        return

    with sqlite3.connect('Users.db') as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM banned_users WHERE UserId = ?", (user_id_to_unban,))
        if not cursor.fetchone():
            bot.send_message(message.chat.id, f"User {user_id_to_unban} is not banned.")
            logger.info(f"Attempt to unban user {user_id_to_unban} who is not banned.")
            return

        conn.execute("DELETE FROM banned_users WHERE UserId = ?", (user_id_to_unban,))
        conn.commit()

    bot.send_message(message.chat.id, f"✅ User {user_id_to_unban} has been unbanned.")
    logger.info(f"Admin {message.from_user.id} unbanned user {user_id_to_unban}.")

if __name__ == '__main__':
    proverka_bd()
    logger.info("Bot started and polling...")
    bot.polling(none_stop=True)

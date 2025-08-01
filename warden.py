import telebot
import json
import os
import re
from collections import defaultdict
from dotenv import load_dotenv
from datetime import datetime, timedelta
from colorama import Fore, Style, init

init(autoreset=True)

load_dotenv()

TOKEN = os.getenv('TOKEN')
DATA_FILE = 'data.json'

bot = telebot.TeleBot(TOKEN)

try:
    with open(DATA_FILE, 'r') as file:
        data = json.load(file)
        message_counts = defaultdict(int, data.get('message_counts', {}))
        user_count = data.get('user_count', 0)
        admin_count = data.get('admin_count', 0)
        muted_count = data.get('muted_count', 0)
        users = data.get('users', {})
except FileNotFoundError:
    data = {}
    message_counts = defaultdict(int)
    user_count = 0
    admin_count = 0
    muted_count = 0
    users = {}


def save_data():
    data['message_counts'] = dict(message_counts)
    data['user_count'] = user_count
    data['admin_count'] = admin_count
    data['muted_count'] = muted_count
    data['users'] = users

    with open(DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)


def escape_markdown_v2(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)


@bot.message_handler(commands=['messages_stats'])
def handle_stats(message):
    if message.from_user.username:
        users[message.from_user.username.lower()] = message.from_user.id
        save_data()

    sorted_users = sorted(message_counts.items(), key=lambda x: x[1], reverse=True)

    stats_message = '💬 Статистика сообщений:\n'
    stats_message += '\n'.join([
        f'{escape_markdown_v2(bot.get_chat_member(message.chat.id, user_id).user.first_name)} {" ".join(filter(None, [escape_markdown_v2(bot.get_chat_member(message.chat.id, user_id).user.last_name)]))} - {count}'
        for user_id, count in sorted_users
    ])

    bot.send_message(
        chat_id=message.chat.id,
        text=stats_message,
        parse_mode='MarkdownV2'
    )

    print(Fore.CYAN + f'Команда /messages_stats вызвана пользователем {message.from_user.first_name}')


@bot.message_handler(commands=['check_perms'])
def check_perms(message):
    if message.from_user.username:
        users[message.from_user.username.lower()] = message.from_user.id
        save_data()

    chat_id = message.chat.id
    bot_member = bot.get_chat_member(chat_id, bot.get_me().id)

    can_delete_messages = bot_member.can_delete_messages
    can_restrict_members = bot_member.can_restrict_members
    can_promote_members = bot_member.can_promote_members

    admin_info = '✅ Бот имеет права администратора:\n'
    admin_info += f'Удаление сообщений: {"✅" if can_delete_messages else "❌"}\n'
    admin_info += f'Блокировка пользователей: {"✅" if can_restrict_members else "❌"}\n'
    admin_info += f'Назначение админов: {"✅" if can_promote_members else "❌"}'

    bot.send_message(
        chat_id=message.chat.id,
        text=admin_info
    )

    print(Fore.MAGENTA + f'Команда /check_perms вызвана пользователем {message.from_user.first_name}')


@bot.message_handler(commands=['add_admin'])
def add_admin(message):
    global admin_count

    if message.from_user.username:
        users[message.from_user.username.lower()] = message.from_user.id
        save_data()

    if message.chat.type not in ['group', 'supergroup']:
        bot.send_message(
            chat_id=message.chat.id,
            text='Эта команда доступна только в группах 🚫'
        )

        return

    bot_member = bot.get_chat_member(message.chat.id, bot.get_me().id)

    if not bot_member.can_promote_members:
        bot.send_message(
            chat_id=message.chat.id,
            text='У меня нет прав назначать администраторов 🚫'
        )

        return

    user_id = None

    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id

    else:
        username = extract_username(message.text)

        if username:
            user_id = users.get(username.lower())

    if not user_id:
        bot.send_message(
            chat_id=message.chat.id,
            text='Пожалуйста, ответьте на сообщение пользователя или упомяните его, чтобы сделать администратором 👈'
        )

        return

    bot.promote_chat_member(
        chat_id=message.chat.id,
        user_id=user_id,
        can_change_info=True,
        can_delete_messages=True,
        can_invite_users=True,
        can_restrict_members=True,
        can_pin_messages=True,
        can_promote_members=True
    )

    admin_count += 1
    save_data()

    bot.send_message(
        chat_id=message.chat.id,
        text=f'{escape_markdown_v2(bot.get_chat_member(message.chat.id, user_id).user.first_name)} {" ".join(filter(None, [escape_markdown_v2(bot.get_chat_member(message.chat.id, user_id).user.last_name)]))} теперь администратор 👑'
    )

    print(Fore.YELLOW + f'Команда /add_admin вызвана пользователем {message.from_user.first_name}')


@bot.message_handler(commands=['delete_admin'])
def delete_admin(message):
    global admin_count

    if message.from_user.username:
        users[message.from_user.username.lower()] = message.from_user.id
        save_data()

    if message.chat.type not in ['group', 'supergroup']:
        bot.send_message(
            chat_id=message.chat.id,
            text='Эта команда доступна только в группах 🚫'
        )

        return

    bot_member = bot.get_chat_member(message.chat.id, bot.get_me().id)
    if not bot_member.can_promote_members:
        bot.send_message(
            chat_id=message.chat.id,
            text='У меня нет прав снимать администраторов 🚫'
        )

        return

    user_id = None

    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id

    else:
        username = extract_username(message.text)

        if username:
            user_id = users.get(username.lower())

    if not user_id:
        bot.send_message(
            chat_id=message.chat.id,
            text='Пожалуйста, ответьте на сообщение пользователя или упомяните его, чтобы снять с должности администратора 👈'
        )

        return

    bot.promote_chat_member(
        chat_id=message.chat.id,
        user_id=user_id,
        can_change_info=False,
        can_delete_messages=False,
        can_invite_users=False,
        can_restrict_members=False,
        can_pin_messages=False,
        can_promote_members=False
    )

    admin_count -= 1
    save_data()

    bot.send_message(
        chat_id=message.chat.id,
        text=f'{escape_markdown_v2(bot.get_chat_member(message.chat.id, user_id).user.first_name)} {" ".join(filter(None, [escape_markdown_v2(bot.get_chat_member(message.chat.id, user_id).user.last_name)]))} больше не администратор 🚫'
    )

    print(Fore.YELLOW + f'Команда /delete_admin вызвана пользователем {message.from_user.first_name}')


@bot.message_handler(commands=['mute'])
def mute_user(message):
    global muted_count

    if message.from_user.username:
        users[message.from_user.username.lower()] = message.from_user.id
        save_data()

    if message.chat.type not in ['group', 'supergroup']:
        bot.send_message(
            chat_id=message.chat.id,
            text='Эта команда доступна только в группах 🚫'
        )

        return

    bot_member = bot.get_chat_member(message.chat.id, bot.get_me().id)

    if not bot_member.can_restrict_members:
        bot.send_message(
            chat_id=message.chat.id,
            text='У меня нет прав ограничивать пользователей 🚫'
        )

        return

    user_id = None

    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id

    else:
        username = extract_username(message.text)

        if username:
            user_id = users.get(username.lower())

    if not user_id:
        bot.send_message(
            chat_id=message.chat.id,
            text='Пожалуйста, ответьте на сообщение пользователя или упомяните его, чтобы замутить 👈'
        )

        return

    try:
        parts = message.text.split(' ', 3)

        if len(parts) == 4:
            _, username, minutes, *reason = parts
            minutes = int(minutes)

        else:
            _, minutes, *reason = parts
            minutes = int(minutes)

        reason = ' '.join(reason) if reason else 'Не указана'
    except (IndexError, ValueError):
        bot.send_message(
            chat_id=message.chat.id,
            text='Использование: /mute @username [минуты] [причина] или /mute [минуты] [причина] 🔇'
        )

        return

    until_date = datetime.now() + timedelta(minutes=minutes)
    bot.restrict_chat_member(
        chat_id=message.chat.id,
        user_id=user_id,
        until_date=until_date.timestamp(),
        can_send_messages=False
    )

    muted_count += 1
    save_data()

    bot.send_message(
        chat_id=message.chat.id,
        text=f'{escape_markdown_v2(bot.get_chat_member(message.chat.id, user_id).user.first_name)} {" ".join(filter(None, [escape_markdown_v2(bot.get_chat_member(message.chat.id, user_id).user.last_name)]))} замучен на {minutes} минут. Причина: {reason} 🔇'
    )

    print(Fore.RED + f'Команда /mute вызвана пользователем {message.from_user.first_name} для {bot.get_chat_member(message.chat.id, user_id).user.first_name}')


@bot.message_handler(commands=['update_users'])
def update_users(message):
    global user_count

    if message.from_user.username:
        users[message.from_user.username.lower()] = message.from_user.id
        save_data()

    user_count = bot.get_chat_members_count(message.chat.id)
    save_data()

    bot.send_message(
        chat_id=message.chat.id,
        text=f'Количество пользователей обновлено: {user_count} 👥'
    )

    print(Fore.BLUE + f'Команда /update_users вызвана пользователем {message.from_user.first_name}')


@bot.message_handler(commands=['bot_stats'])
def bot_stats(message):
    if message.from_user.username:
        users[message.from_user.username.lower()] = message.from_user.id
        save_data()

    stats_message = '📊 Статистика бота:\n'
    stats_message += f'👥 Пользователей: {user_count}\n'
    stats_message += f'👑 Администраторов: {admin_count}\n'
    stats_message += f'🔇 Замученных: {muted_count}'

    bot.send_message(
        chat_id=message.chat.id,
        text=stats_message
    )

    print(Fore.BLUE + f'Команда /bot_stats вызвана пользователем {message.from_user.first_name}')


@bot.message_handler(commands=['help'])
def handle_help(message):
    if message.from_user.username:
        users[message.from_user.username.lower()] = message.from_user.id
        save_data()

    help_text = '👋 Бот-администратор\nКоманды:\n'
    help_text += '/mute @username [минуты] [причина] или /mute [минуты] [причина] — запретить пользователю возможность писать в чат 🔇\n'
    help_text += '/add_admin @username или /add_admin — добавить администратора 👑\n'
    help_text += '/delete_admin @username или /delete_admin — снять администратора 🚫\n'
    help_text += '/check_perms — проверить права бота ✅\n'
    help_text += '/messages_stats — статистика сообщений 💬\n'
    help_text += '/bot_stats — общая статистика бота 📊\n'
    help_text += '/update_users — обновить количество пользователей 👥\n'

    bot.send_message(
        chat_id=message.chat.id,
        text=help_text
    )

    print(Fore.BLUE + f'Команда /help вызвана пользователем {message.from_user.first_name}')

@bot.message_handler(func=lambda message: True)
def count_messages(message):
    if message.from_user.username:
        users[message.from_user.username.lower()] = message.from_user.id
        save_data()

    user_id = message.from_user.id
    message_counts[user_id] += 1

    save_data()


def extract_username(text):
    words = text.split()

    for word in words:
        if word.startswith('@'):
            return word[1:]


bot.skip_pending = True

print(Fore.LIGHTGREEN_EX + 'Бот запущен!')

bot.polling()

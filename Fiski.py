import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import random
import math

import config

TOKEN = config.tokenFiski  # Укажи свой токен
bot = telebot.TeleBot(TOKEN)

PI = 3.14
users = {}  # {user_id: {'correct': 0, 'incorrect': 0, 'name': 'Имя'} }
admins = set()  # Хранение админов
SECRET_CODE = "404.498"


# Главное меню
@bot.message_handler(commands=["start"])
def start_command(message):
    user_id = message.chat.id
    if user_id not in users:
        bot.send_message(user_id, "Привет! Введи свое имя для регистрации.")
        bot.register_next_step_handler(message, register_user)
    else:
        show_main_menu(user_id)
def register_user(message):
    user_id = message.chat.id
    users[user_id] = {'correct': 0, 'incorrect': 0, 'name': message.text}
    bot.send_message(user_id, "Ты зарегистрирован!")
    notify_admins(user_id)
    show_main_menu(user_id)


def notify_admins(user_id):
    user_data = users[user_id]
    for admin_id in admins:
        bot.send_message(admin_id, f"📢 Новый пользователь:\nИмя: {user_data['name']}\n"
                                   f"Правильных ответов: {user_data['correct']}\n"
                                   f"Неправильных ответов: {user_data['incorrect']}")


def show_main_menu(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Алгебра", "Геометрия", "Вероятность и Статистика", "Статистика")
    bot.send_message(user_id, "Выбери категорию:", reply_markup=markup)


# Выбор подкатегории
@bot.message_handler(content_types=["text"])
def handle_text(message):
    user_id = message.chat.id
    text = message.text

    if text == SECRET_CODE:
        admins.add(user_id)
        bot.send_message(user_id, "✅ Теперь ты админ! Вот статистика пользователей:")
        send_all_users_stats(user_id)
        return

    if text == "Алгебра":
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Возведение в степень", "Извлечение корня", "Системы уравнений", "Назад")
        bot.send_message(user_id, "Выбери тему:", reply_markup=markup)

    elif text == "Геометрия":
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Геометрия", "Тригонометрия", "Назад")
        bot.send_message(user_id, "Выбери тему:", reply_markup=markup)

    elif text == "Вероятность и Статистика":
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вероятность", "Статистика", "Назад")
        bot.send_message(user_id, "Выбери тему:", reply_markup=markup)

    elif text == "Статистика":
        show_statistics(user_id)

    elif text == "Назад":
        show_main_menu(user_id)

    else:
        send_task(user_id, text)


def send_task(user_id, topic):
    if topic == "Возведение в степень":
        base = random.randint(2, 10)
        question = f"Вычисли: {base}²"
        answer = str(base ** 2)
    elif topic == "Извлечение корня":
        base = random.randint(2, 10)
        question = f"Найди корень: √{base ** 2}"
        answer = str(base)
    elif topic == "Системы уравнений":
        x, y = random.randint(-5, 5), random.randint(-5, 5)
        a, b = random.randint(1, 5), random.randint(1, 5)
        c = a * x + b * y
        d, e = random.randint(1, 5), random.randint(1, 5)
        f = d * x + e * y
        question = f"Реши систему:\n{a}x + {b}y = {c}\n{d}x + {e}y = {f}"
        answer = f"({x}; {y})"
    elif topic == "Геометрия":
        r = random.randint(5, 15)
        question = f"Найди площадь круга с радиусом {r} (π≈3.14)."
        answer = str(round(PI * r ** 2, 2))
    elif topic == "Тригонометрия":
        angle = random.choice([0, 30, 45, 60, 90, 180])
        question = f"Чему равно sin({angle})?"
        answer = str(round(math.sin(math.radians(angle)), 3))
    elif topic == "Вероятность":
        total = random.randint(20, 50)
        favorable = random.randint(1, total)
        question = f"В урне {total} шаров, {favorable} белых. Какова вероятность вытащить белый?"
        answer = str(round(favorable / total, 3))
    elif topic == "Статистика":
        numbers = [random.randint(1, 100) for _ in range(5)]
        question = f"Найди среднее арифметическое: {', '.join(map(str, numbers))}"
        answer = str(round(sum(numbers) / len(numbers), 3))
    else:
        bot.send_message(user_id, "Я не понимаю эту команду.")
        return

    msg = bot.send_message(user_id, question)
    bot.register_next_step_handler(msg, check_answer, answer)


def check_answer(message, answer):
    """ Проверка ответа пользователя """
    user_id = message.chat.id
    user_input = message.text.strip().replace(",", ".")

    # Проверяем, зарегистрирован ли пользователь
    if user_id not in users:
        users[user_id] = {'correct': 0, 'incorrect': 0, 'name': f'Пользователь {user_id}'}

    if user_input == answer:
        users[user_id]['correct'] += 1
        bot.send_message(user_id, "✅ Правильно! Молодец!")
    else:
        users[user_id]['incorrect'] += 1
        bot.send_message(user_id, f"❌ Неправильно. Правильный ответ: {answer}.")

    show_main_menu(user_id)

def show_statistics(user_id):
    """ Показ статистики пользователя """
    stats = users.get(user_id, {'correct': 0, 'incorrect': 0})
    bot.send_message(user_id, f"📊 Твоя статистика:\n✅ Правильных: {stats['correct']}\n❌ Неправильных: {stats['incorrect']}")


def send_all_users_stats(admin_id):
    """ Отправляет админу статистику всех пользователей """
    if not users:
        bot.send_message(admin_id, "Нет зарегистрированных пользователей.")
        return

    stats_message = "📊 Статистика всех пользователей:\n"
    for user_id, data in users.items():
        stats_message += f"👤 {data['name']} - ✅ {data['correct']} | ❌ {data['incorrect']}\n"

    bot.send_message(admin_id, stats_message)


if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)
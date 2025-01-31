import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import random
import math

import config

TOKEN = config.tokenBD
bot = telebot.TeleBot(TOKEN)

users = {}

# Задачи по категориям
tasks = {
    "Алгебра": [],
    "Геометрия": [],
    "Статистика": [],
    "Теория вероятностей": []
}

PI = 3.14

def format_number(value):
    formatted = "{:.3f}".format(value).rstrip("0").rstrip(".")
    return "0" if formatted == "-0" else formatted


# Генерация задач
def generate_tasks():
    global tasks

    # Алгебра
    for _ in range(10):
        base = random.randint(1, 24)  # Двузначные числа (0 < x < 25)
        squared = base ** 2
        root = math.sqrt(squared)
        tasks["Алгебра"].append({"question": f"Вычисли: {base}²", "answer": str(squared)})
        tasks["Алгебра"].append({"question": f"Найди корень: √{squared}", "answer": str(int(root))})

    # Системы уравнений (только целые решения, формат (x, y) или (x; y))
    for _ in range(10):
        x, y = random.randint(-10, 10), random.randint(-10, 10)
        a, b = random.randint(1, 10), random.randint(1, 10)
        c = a * x + b * y
        d, e = random.randint(1, 10), random.randint(1, 10)
        f = d * x + e * y
        tasks["Алгебра"].append({
            "question": f"Реши систему:\n{a}x + {b}y = {c}\n{d}x + {e}y = {f}",
            "answer": f"({x}; {y})"
        })

    # Геометрия (используем PI = 3.14)
    for _ in range(10):
        radius = random.randint(5, 20)
        area = format_number(PI * radius ** 2)
        circumference = format_number(2 * PI * radius)
        tasks["Геометрия"].append({"question": f"Найди площадь круга с радиусом {radius}.", "answer": area})
        tasks["Геометрия"].append({"question": f"Найди длину окружности с радиусом {radius}.", "answer": circumference})

    # Тригонометрия с разными разрешёнными углами
    sin_angles = [0, 30, 90, 150, 180, 210, 270, 330, 360]
    cos_angles = [0, 60, 90, 120, 180, 240, 270, 300, 360]
    tan_angles = [0, 45, 135, 180, 225, 315, 360]

    for _ in range(10):
        sin_angle = random.choice(sin_angles)
        cos_angle = random.choice(cos_angles)
        tan_angle = random.choice(tan_angles)

        sin_val = format_number(math.sin(math.radians(sin_angle)))
        cos_val = format_number(math.cos(math.radians(cos_angle)))
        tan_val = format_number(math.tan(math.radians(tan_angle))) if tan_angle not in [90, 270] else "не существует"

        tasks["Геометрия"].append({"question": f"Чему равно sin({sin_angle})?", "answer": sin_val})
        tasks["Геометрия"].append({"question": f"Чему равно cos({cos_angle})?", "answer": cos_val})
        if tan_angle not in [90, 270]:
            tasks["Геометрия"].append({"question": f"Чему равно tan({tan_angle})?", "answer": tan_val})

    # Теория вероятностей (исключены бесконечные дроби, максимум 3 знака после запятой)
    for _ in range(10):
        while True:
            total = random.randint(20, 100)
            favorable = random.randint(1, total)
            probability = favorable / total
            if len(str(probability).split(".")[1]) <= 3:  # Проверяем количество знаков после запятой
                break
        answer = str(int(probability)) if probability.is_integer() else str(probability)
        tasks["Теория вероятностей"].append({
            "question": f"В мешке {total} шаров, {favorable} белых. Какова вероятность достать белый шар?",
            "answer": answer
        })

    # Статистика (исключены бесконечные дроби, максимум 3 знака после запятой)
    for _ in range(10):
        numbers = [random.randint(1, 100) for _ in range(random.randint(5, 10))]
        mean_value = sum(numbers) / len(numbers)
        if len(str(mean_value).split(".")[1]) > 3:
            continue  # Пропускаем случаи с длинной дробной частью
        answer = str(int(mean_value)) if mean_value.is_integer() else str(mean_value)
        tasks["Статистика"].append({
            "question": f"Найди среднее арифметическое чисел: {', '.join(map(str, numbers))}",
            "answer": answer
        })

generate_tasks()


@bot.message_handler(commands=["start"])
def start_command(message):
    user_id = message.chat.id
    if user_id not in users:
        users[user_id] = {"name": message.chat.first_name, "score": 0}
        bot.send_message(user_id, f"Привет, {message.chat.first_name}! Ты зарегистрирован.")
    show_main_menu(user_id)


def show_main_menu(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Математика"))
    bot.send_message(user_id, "Выбери категорию:", reply_markup=markup)


def show_math_menu(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Алгебра"), KeyboardButton("Геометрия"))
    markup.add(KeyboardButton("Теория вероятностей"), KeyboardButton("Статистика"))
    markup.add(KeyboardButton("Назад"))
    bot.send_message(user_id, "Выбери раздел:", reply_markup=markup)


@bot.message_handler(content_types=["text"])
def handle_text(message):
    user_id = message.chat.id
    text = message.text

    if text == "Математика":
        show_math_menu(user_id)
    elif text in tasks:
        send_task(user_id, text)
    elif text == "Назад":
        show_main_menu(user_id)
    else:
        bot.send_message(user_id, "Я не понимаю эту команду.")


def send_task(user_id, category):
    task = random.choice(tasks[category])
    bot.send_message(user_id, task["question"])
    bot.register_next_step_handler_by_chat_id(user_id, check_answer, task, category)


def check_answer(message, task, category):
    user_id = message.chat.id
    user_input = message.text.strip().replace(",", ".")

    # Проверка наличия пользователя в словаре
    if user_id not in users:
        users[user_id] = {"name": message.chat.first_name, "score": 0}

    if user_input == task["answer"]:
        users[user_id]["score"] += 1
        bot.send_message(user_id, "Правильно! Молодец!")
    else:
        bot.send_message(user_id, f"Неправильно. Правильный ответ: {task['answer']}")

    show_math_menu(user_id)


if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)

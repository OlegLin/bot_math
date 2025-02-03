import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import random
import math
import sqlite3
import threading
TOKEN = "7932798585:AAGJeTAXwGWNY59ejvLhQBjiDBh2QcniFP4"
bot = telebot.TeleBot(TOKEN)

# Подключение к БД
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
# Функция для создания соединения с БД в новом потоке
def get_db_connection():
    local_conn = sqlite3.connect("users.db", check_same_thread=False)
    return local_conn, local_conn.cursor()

# Создание таблицы пользователей
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    ИМЯ_ПОЛЬЗОВАТЕЛЯ TEXT,
    ПРАВИЛЬНЫХ_ОТВЕТОВ INTEGER DEFAULT 0,
    НЕПРАВИЛЬНЫХ_ОТВЕТОВ INTEGER DEFAULT 0,
    АДМИН INTEGER DEFAULT 0,
    ЗАБЛОКИРОВАН INTEGER DEFAULT 0
)
""")
conn.commit()

# Администраторы
ADMINS = set()

# Функция уведомления администраторов
def notify_admins(message):
    for admin in ADMINS:
        bot.send_message(admin, message)

# Функция регистрации пользователя
def register_user(user_id, name):
    conn, cursor = get_db_connection()
    try:
        # Проверяем, существует ли пользователь в базе
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        existing_user = cursor.fetchone()

        # Если пользователя нет, добавляем его с именем
        if existing_user is None:
            cursor.execute("INSERT INTO users (user_id, ИМЯ_ПОЛЬЗОВАТЕЛЯ) VALUES (?, ?)", (user_id, name))
            conn.commit()
            notify_admins(f"Новый пользователь: {name} (ID: {user_id})")  # Уведомляем администраторов о новом пользователе
        else:
            # Если имя не задано, обновляем его
            current_name = existing_user[1]
            if current_name != name:
                cursor.execute("UPDATE users SET ИМЯ_ПОЛЬЗОВАТЕЛЯ = ? WHERE user_id = ?", (name, user_id))
                conn.commit()
    finally:
        cursor.close()  # Закрываем курсор
        conn.close()

# Функция обработки первого сообщения от пользователя
def handle_user_first_message(message):
    user_id = message.chat.id
    name = message.chat.first_name
    register_user(user_id, name)

    # Показываем меню математики после регистрации
    show_math_menu(user_id)

# Функция проверки ответа в потоке
def check_answer_thread(message, task, category):
    user_id = message.chat.id
    user_input = message.text.strip().replace(",", ".")

    def task_func():
        conn, cursor = get_db_connection()
        try:
            cursor.execute("SELECT ПРАВИЛЬНЫХ_ОТВЕТОВ, НЕПРАВИЛЬНЫХ_ОТВЕТОВ FROM users WHERE user_id = ?",
                           (user_id,))
            result = cursor.fetchone()

            if result is None:
                register_user(user_id, message.chat.first_name)
                ПРАВИЛЬНЫХ_ОТВЕТОВ, НЕПРАВИЛЬНЫХ_ОТВЕТОВ = 0, 0
            else:
                ПРАВИЛЬНЫХ_ОТВЕТОВ, НЕПРАВИЛЬНЫХ_ОТВЕТОВ = result

            if user_input == task["answer"]:
                ПРАВИЛЬНЫХ_ОТВЕТОВ += 1
                bot.send_message(user_id, "Правильно! Молодец!")
            else:
                НЕПРАВИЛЬНЫХ_ОТВЕТОВ += 1
                bot.send_message(user_id, f"Неправильно. Правильный ответ: {task['answer']}")

            cursor.execute("UPDATE users SET ПРАВИЛЬНЫХ_ОТВЕТОВ = ?, НЕПРАВИЛЬНЫХ_ОТВЕТОВ = ? WHERE user_id = ?",
                           (ПРАВИЛЬНЫХ_ОТВЕТОВ, НЕПРАВИЛЬНЫХ_ОТВЕТОВ, user_id))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

        show_math_menu(user_id)

    threading.Thread(target=task_func).start()



# Функция проверки и добавления колонки ЗАБЛОКИРОВАН
def ensure_block_column():
    cursor.execute("PRAGMA table_info(users);")
    columns = [row[1] for row in cursor.fetchall()]
    if "ЗАБЛОКИРОВАН" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN ЗАБЛОКИРОВАН INTEGER DEFAULT 0;")
        conn.commit()

ensure_block_column()  # Проверяем колонку при запуске

# Функция проверки, заблокирован ли пользователь
def is_user_blocked(user_id):
    conn = sqlite3.connect("users.db")  # Открываем соединение
    cursor = conn.cursor()
    cursor.execute("SELECT ЗАБЛОКИРОВАН FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()  # Закрываем соединение
    return result is not None and result[0] == 1  # Проверяем, есть ли пользователь и заблокирован ли он


# Фильтр: если пользователь заблокирован, бот его игнорирует
@bot.message_handler(func=lambda message: is_user_blocked(message.chat.id))
def ignore_blocked_users(message):
    pass  # Просто ничего не делаем

# Функция блокировки/разблокировки пользователя
def block_user(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ЗАБЛОКИРОВАН FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if result is None:
        conn.close()
        return False  # Пользователя нет в базе, не блокируем

    if result[0] == 1:  # Если уже заблокирован, разблокируем
        cursor.execute("UPDATE users SET ЗАБЛОКИРОВАН = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        bot.send_message(user_id, "Вы были разблокированы администратором.")
        return False
    else:  # Если не заблокирован, блокируем
        cursor.execute("UPDATE users SET ЗАБЛОКИРОВАН = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        bot.send_message(user_id, "Вы были заблокированы администратором.")
        return True


# Функция назначения администратора
def make_admin(user_id):
    global conn  # Работаем с глобальным соединением
    try:
        # Проверяем, есть ли соединение с БД
        if conn is None:
            conn = sqlite3.connect("users.db")  # Открываем заново
        cursor = conn.cursor()

        cursor.execute("UPDATE users SET АДМИН = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        ADMINS.add(user_id)

    except sqlite3.Error as e:  # Ловим ошибки работы с БД
        print(f"Ошибка БД: {e}")
        bot.send_message(user_id, "❌ Ошибка при назначении администратора.")
    finally:
        try:
            cursor.close()  # Закрываем курсор
        except NameError:
            pass  # Если курсор не был создан, просто игнорируем ошибк

# Функция разблокировки пользователя
def unblock_user(user_id):
    cursor.execute("UPDATE users SET ЗАБЛОКИРОВАН = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(user_id, "Вы были разблокированы администратором.")

# Обработчик для проверки заданий другого пользователя
@bot.message_handler(func=lambda message: message.text == "Проверить задания другого пользователя")
def handle_check_user_tasks(message):
    user_id = message.chat.id
    bot.send_message(user_id, "Введите ID пользователя для проверки:")
    bot.register_next_step_handler(message, process_check_user_tasks)

# Обработчик для блокировки пользователя
@bot.message_handler(func=lambda message: message.text == "Заблокировать пользователя")
def handle_block_user(message):
    user_id = message.chat.id
    bot.send_message(user_id, "Введите ID пользователя для блокировки:")
    bot.register_next_step_handler(message, process_block_user)

# Обработчик ввода ID пользователя для проверки заданий
def process_check_user_tasks(message):
    user_id = message.chat.id
    target_user_id = message.text.strip()

    if target_user_id.isdigit():
        target_user_id = int(target_user_id)
        check_user_tasks(user_id, target_user_id)
    else:
        bot.send_message(user_id, "Пожалуйста, введите корректный ID пользователя.")


# Обработчик ввода ID пользователя для блокировки/разблокировки
def process_block_user(message):
    user_id = message.chat.id
    target_user_id = message.text.strip()

    if target_user_id.isdigit():
        target_user_id = int(target_user_id)
        if target_user_id == user_id:
            bot.send_message(user_id, "Вы не можете заблокировать/разблокировать самого себя!")
            return

        action = block_user(target_user_id)  # Блокировка или разблокировка
        if action:
            bot.send_message(user_id, f"Пользователь с ID {target_user_id} заблокирован.")
        else:
            bot.send_message(user_id, f"Пользователь с ID {target_user_id} разблокирован.")
    else:
        bot.send_message(user_id, "Пожалуйста, введите корректный ID пользователя.")

# Функция проверки заданий другого пользователя
def check_user_tasks(admin_id, target_user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ПРАВИЛЬНЫХ_ОТВЕТОВ, НЕПРАВИЛЬНЫХ_ОТВЕТОВ FROM users WHERE user_id = ?", (target_user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        ПРАВИЛЬНЫХ_ОТВЕТОВ, НЕПРАВИЛЬНЫХ_ОТВЕТОВ = result
        bot.send_message(admin_id, f"Статистика пользователя (ID: {target_user_id}):\n✔️ Правильных ответов: {ПРАВИЛЬНЫХ_ОТВЕТОВ}\n❌ Неправильных ответов: {НЕПРАВИЛЬНЫХ_ОТВЕТОВ}")
    else:
        bot.send_message(admin_id, f"Нет данных для пользователя с ID: {target_user_id}.")

# Функция загрузки админов из БД
def load_admins():
    cursor.execute("SELECT user_id FROM users WHERE АДМИН = 1")
    for row in cursor.fetchall():
        ADMINS.add(row[0])

load_admins()

users = {}

tasks = {
    "Корни": [],
    "Степени": [],
    "Системы уравнений": [],
    "Площадь окружности": [],
    "Длина окружности": [],
    "Тригонометрия": [],
    "Вероятность": [],
    "Среднее арифметическое": []
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
        tasks["Степени"].append({"question": f"Вычисли: {base}²", "answer": str(squared)})
        tasks["Корни"].append({"question": f"Найди корень: √{squared}", "answer": str(int(root))})

    # Системы уравнений (только целые решения, формат (x, y) или (x; y))
    for _ in range(10):
        x, y = random.randint(-10, 10), random.randint(-10, 10)
        a, b = random.randint(1, 10), random.randint(1, 10)
        c = a * x + b * y
        d, e = random.randint(1, 10), random.randint(1, 10)
        f = d * x + e * y
        tasks["Системы уравнений"].append({
            "question": f"Реши систему:\n{a}x + {b}y = {c}\n{d}x + {e}y = {f}",
            "answer": f"({x}; {y})"
        })

    # Геометрия (используем PI = 3.14)
    for _ in range(10):
        radius = random.randint(5, 20)
        area = format_number(PI * radius ** 2)
        circumference = format_number(2 * PI * radius)
        tasks["Площадь окружности"].append({"question": f"Найди площадь круга с радиусом {radius}.", "answer": area})
        tasks["Длина окружности"].append({"question": f"Найди длину окружности с радиусом {radius}.", "answer": circumference})

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

        tasks["Тригонометрия"].append({"question": f"Чему равно sin({sin_angle})?", "answer": sin_val})
        tasks["Тригонометрия"].append({"question": f"Чему равно cos({cos_angle})?", "answer": cos_val})
        if tan_angle not in [90, 270]:
            tasks["Тригонометрия"].append({"question": f"Чему равно tan({tan_angle})?", "answer": tan_val})

    # Теория вероятностей (исключены бесконечные дроби, максимум 3 знака после запятой)
    for _ in range(10):
        while True:
            total = random.randint(20, 100)
            favorable = random.randint(1, total)
            probability = favorable / total
            if len(str(probability).split(".")[1]) <= 3:  # Проверяем количество знаков после запятой
                break
        answer = str(int(probability)) if probability.is_integer() else str(probability)
        tasks["Вероятность"].append({
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
        tasks["Среднее арифметическое"].append({
            "question": f"Найди среднее арифметическое чисел: {', '.join(map(str, numbers))}",
            "answer": answer
        })

generate_tasks()


def show_main_menu(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)

    if user_id in ADMINS:
        # Если пользователь администратор, добавляем дополнительные кнопки
        markup.add(KeyboardButton("Математика"))
        markup.add(KeyboardButton("Проверить статистику"))
        markup.add(KeyboardButton("Заблокировать пользователя"))
        markup.add(KeyboardButton("Проверить задания другого пользователя"))
    else:
        # Если пользователь обычный, показываем только основные кнопки
        markup.add(KeyboardButton("Математика"))

    bot.send_message(user_id, "Выбери категорию:", reply_markup=markup)

@bot.message_handler(content_types=["text"])
def handle_text(message, markup=None):
    user_id = message.chat.id
    text = message.text

    if text == "admin404":
        make_admin(user_id)
        bot.send_message(user_id, "✅Вы стали администратором!✅")
        return

    if text == "Математика":
        show_math_menu(user_id)
    if text == "Алгебра":
        show_matem_menu(user_id)
    if text == "Геометрия":
        show_geometry_menu(user_id)
    if text == "Теория вероятностей":
        show_terver_menu(user_id)
    if text == "Статистика":
        show_statis_menu(user_id)
    elif text == "Проверить задания другого пользователя":
        bot.send_message(user_id, "Введите ID пользователя для проверки:")
        bot.register_next_step_handler(message, handle_check_user_tasks)
    elif text == "Заблокировать пользователя":
        bot.send_message(user_id, "Введите ID пользователя для блокировки:")
        bot.register_next_step_handler(message, handle_block_user)
    elif text == "Статистика по всем заданиям":
        show_statistics(user_id)
    elif text in tasks:
        send_task(user_id, text)
    elif text == "Назад":
        show_main_menu(user_id)
    elif text == "назад":
        show_math_menu(user_id)


def show_math_menu(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Алгебра"), KeyboardButton("Геометрия"))
    markup.add(KeyboardButton("Теория вероятностей"), KeyboardButton("Статистика"))
    markup.add(KeyboardButton("Статистика по всем заданиям"))
    markup.add(KeyboardButton("Назад"))
    bot.send_message(user_id, "Выбери раздел:", reply_markup=markup)



def show_matem_menu(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Корни"),KeyboardButton("Степени"), KeyboardButton("Системы уравнений"))
    markup.add(KeyboardButton("назад"))
    bot.send_message(user_id, "Выбери задачу:", reply_markup=markup)


def show_geometry_menu(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Площадь окружности"), KeyboardButton("Длина окружности"), KeyboardButton("Тригонометрия"))
    markup.add(KeyboardButton("назад"))
    bot.send_message(user_id, "Выбери задачу:", reply_markup=markup)


def show_terver_menu(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Вероятность")),
    markup.add(KeyboardButton("назад"))
    bot.send_message(user_id, "Выбери задачу:", reply_markup=markup)


def show_statis_menu(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Среднее арифметическое")),
    markup.add(KeyboardButton("назад"))
    bot.send_message(user_id, "Выбери задачу:", reply_markup=markup)


# Функция проверки ответа (выполняется в отдельном потоке)
def check_answer_thread(message, task, category):
    user_id = message.chat.id
    user_input = message.text.strip().replace(",", ".")

    def task_func():
        conn, cursor = get_db_connection()
        try:
            cursor.execute("SELECT ПРАВИЛЬНЫХ_ОТВЕТОВ, НЕПРАВИЛЬНЫХ_ОТВЕТОВ FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()

            if result is None:
                register_user(user_id, message.chat.first_name)
                ПРАВИЛЬНЫХ_ОТВЕТОВ, НЕПРАВИЛЬНЫХ_ОТВЕТОВ = 0, 0
            else:
                ПРАВИЛЬНЫХ_ОТВЕТОВ, НЕПРАВИЛЬНЫХ_ОТВЕТОВ = result

            if user_input == task["answer"]:
                ПРАВИЛЬНЫХ_ОТВЕТОВ += 1
                bot.send_message(user_id, "Правильно! Молодец!")
            else:
                НЕПРАВИЛЬНЫХ_ОТВЕТОВ += 1
                bot.send_message(user_id, f"Неправильно. Правильный ответ: {task['answer']}")

            cursor.execute("UPDATE users SET ПРАВИЛЬНЫХ_ОТВЕТОВ = ?, НЕПРАВИЛЬНЫХ_ОТВЕТОВ = ? WHERE user_id = ?",
                           (ПРАВИЛЬНЫХ_ОТВЕТОВ, НЕПРАВИЛЬНЫХ_ОТВЕТОВ, user_id))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

        show_math_menu(user_id)

    threading.Thread(target=task_func, daemon=True).start()


# Функция отправки задания
def send_task(user_id, category):
    task = random.choice(tasks[category])
    bot.send_message(user_id, task["question"])
    bot.register_next_step_handler_by_chat_id(user_id, lambda msg: check_answer_thread(msg, task, category))


def handle_check_user_tasks(message):
    user_id = message.chat.id
    target_user_id = message.text.strip()

    if target_user_id.isdigit():
        target_user_id = int(target_user_id)
        check_user_tasks(user_id, target_user_id)
    else:
        bot.send_message(user_id, "Пожалуйста, введите корректный ID пользователя.")

def handle_block_user(message):
    user_id = message.chat.id
    target_user_id = message.text.strip()

    if target_user_id.isdigit():
        target_user_id = int(target_user_id)
        block_user(target_user_id)
        bot.send_message(user_id, f"Пользователь с ID {target_user_id} заблокирован.")
    else:
        bot.send_message(user_id, "Пожалуйста, введите корректный ID пользователя.")

# Функция отображения статистики пользователя
def show_statistics(user_id):
    conn = sqlite3.connect("users.db")  # Открываем соединение
    cursor = conn.cursor()
    cursor.execute("SELECT ПРАВИЛЬНЫХ_ОТВЕТОВ, НЕПРАВИЛЬНЫХ_ОТВЕТОВ FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()  # Закрываем соединение

    if result:
        ПРАВИЛЬНЫХ_ОТВЕТОВ, НЕПРАВИЛЬНЫХ_ОТВЕТОВ = result
        bot.send_message(user_id, f"📊 Ваша статистика:\n✔️ Правильных ответов: {ПРАВИЛЬНЫХ_ОТВЕТОВ}\n❌ Неправильных ответов: {НЕПРАВИЛЬНЫХ_ОТВЕТОВ}")
    else:
        bot.send_message(user_id, "У вас пока нет статистики.")


if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)
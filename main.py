import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from questions import questions

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

ADMIN_ID = 966780974

# Советы для разных типов результатов
ADVICE = {
    "top": (
        "Твой доминирующий центр — верхний 🧠.\n"
        "Ты ищешь партнёра, с которым можно развиваться, мечтать и говорить «на одном языке». "
        "Возможно, тебе не хватает эмоциональной близости (сердечный центр) или телесной страсти и ощущения желания (сексуальный центр)."
    ),
    "heart": (
        "Твой доминирующий центр — сердечный 💚.\n"
        "Ты стремишься к любви, теплу и близости. Возможно, тебе не хватает ощущения, "
        "что партнёр разделяет твои ценности (верхний центр) или сильного телесного влечения (сексуальный центр)."
    ),
    "sex": (
        "Твой доминирующий центр — сексуальный 🔥.\n"
        "Ты живёшь через энергию тела, страсть и притяжение. Возможно, тебе не хватает "
        "душевной глубины и принятия (сердечный центр) или общих целей и смыслов с партнёром (верхний центр)."
    ),
    "balance": (
        "У тебя гармоничное распределение между верхним, сердечным и сексуальным центрами ⚖️.\n"
        "Ты умеешь соединять любовь, разум и страсть в отношениях. Такая внутренняя целостность "
        "помогает тебе выстраивать глубокие, живые и осознанные связи. Сохраняй этот баланс — он редкость и большая сила."
    )
}


# Состояния бота
class Quiz(StatesGroup):
    waiting_for_gender = State()  # Новое состояние для выбора пола
    in_progress = State()
    waiting_for_answer = State()


# Хранение данных пользователей
user_data = {}  # user_id: {"scores": {"top": 0, "heart": 0, "sex": 0}, "gender": None}

# Клавиатура для выбора пола
gender_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Мужчина"), KeyboardButton(text="Женщина")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


# /start
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    user_name = message.from_user.full_name
    await message.answer(
        f"👋 Привет {user_name}!\n\n"
        f"Отношения становятся по-настоящему живыми и гармоничными, \n"
        f"когда соединяются три центра — ценности, чувства и тело.\n"
        f"Этот короткий тест поможет тебе понять,\n"
        f"на каком уровне ты выбираешь партнёра и почему отношения могут не складываться\n\n"
        f"Сначала укажи свой пол:",
        reply_markup=gender_keyboard
    )
    await state.set_state(Quiz.waiting_for_gender)


# Обработка выбора пола
@dp.message(Quiz.waiting_for_gender)
async def process_gender(message: types.Message, state: FSMContext):
    gender = message.text
    user_id = message.from_user.id

    # Сохраняем пол пользователя
    user_data[user_id] = {
        "scores": {"top": 0, "heart": 0, "sex": 0},
        "gender": gender
    }

    await message.answer(
        f"Отлично! Теперь ответь на 9 вопросов, чтобы узнать свой доминирующий центр.",
        reply_markup=types.ReplyKeyboardRemove()  # Убираем клавиатуру
    )

    # Запускаем тест
    await state.set_state(Quiz.in_progress)
    await send_question(user_id, 0)


# Отправка вопроса
async def send_question(user_id: int, question_id: int):
    question = questions[question_id]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=opt["text"], callback_data=f"answer_{question_id}_{opt['center']}")]
        for opt in question["options"]
    ])
    await bot.send_message(user_id, question["text"], reply_markup=keyboard)


# Обработка ответа
@dp.callback_query(lambda c: c.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery, state: FSMContext):
    _, question_id, center = callback.data.split("_")
    user_id = callback.from_user.id

    # Добавляем балл к выбранному центру
    user_data[user_id]["scores"][center] += 1

    # Переход к следующему вопросу или завершение
    next_question_id = int(question_id) + 1
    if next_question_id < len(questions):
        await send_question(user_id, next_question_id)
    else:
        await show_result(user_id)
        await state.clear()


# Показ результата
async def show_result(user_id: int):
    data = user_data[user_id]
    scores = data["scores"]
    gender = data.get("gender", "не указан")

    max_center = max(scores, key=scores.get)
    # min_center = min(scores, key=scores.get)

    # Проверяем баланс
    all_values = list(scores.values())
    if all(v == all_values[0] for v in all_values):
        advice_type = "balance"
    else:
        advice_type = max_center

    result_text = (
        f"🎉 Твой результат ({gender}):\n\n"
        f"🧠 Верхний центр: {scores['top']}\n"
        f"💚 Сердечный центр: {scores['heart']}\n"
        f"🔥 Сексуальный центр: {scores['sex']}\n\n"
        f"{ADVICE[advice_type]}\n\n"

        f'🧭 Хочешь понять, как развить недостающие центры и притянуть настоящие отношения?\n'
        f'📲 Подпишись на канал: «Вместе» https://t.me/unionlevels — там о любви, энергии и взрослом партнёрстве.\n\n'
        f'А так же:\n'
        f'🌿 Присоединяйся к ретриту «ВМЕСТЕ» под Петербургом, \n'
        f'27 июня 2025 — три дня погружения в сердце, тело и дух отношений.'
    )

    await bot.send_message(
        user_id,
        result_text,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="Подписаться на канал", url="https://t.me/unionlevels"),
        ]])
    )
    # Отправка админу
    admin_text = (
        f"📝 Пользователь {user_id} ({gender}) прошёл тест.\n"
        f"Результаты:\n"
        f"Верхний: {scores['top']}, Сердечный: {scores['heart']}, Сексуальный: {scores['sex']}.\n"
        f"Доминирующий центр: {advice_type.upper()}"
    )
    await bot.send_message(ADMIN_ID, admin_text)





# Запуск бота
if __name__ == "__main__":
    dp.run_polling(bot)
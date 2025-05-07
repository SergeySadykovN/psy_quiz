import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton

from questions import questions

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

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
    in_progress = State()
    waiting_for_answer = State()




# Хранение баллов в памяти (user_id: {"top": 0, "heart": 0, "sex": 0})
user_scores = {}


# /start
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    user_name = message.from_user.full_name
    await message.answer(
        f"👋 Привет {user_name}! \n\n"
        f"Отношения становятся по-настоящему живыми и гармоничными, \n"
        f"когда соединяются три центра — ценности, чувства и тело.\n"
        f"Этот короткий тест поможет тебе понять,\n"
        f"на каком уровне ты выбираешь партнёра и почему отношения могут не складываться\n"
        f"Ответь на 9 вопросов, чтобы узнать свой доминирующий центр.",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="Начать тест", callback_data="start_quiz")
        ]])
    )


# Начало теста
@dp.callback_query(lambda c: c.data == "start_quiz")
async def start_quiz(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_scores[user_id] = {"top": 0, "heart": 0, "sex": 0}
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
    user_scores[user_id][center] += 1  # +1 балл выбранному центру

    # Переход к следующему вопросу или завершение
    next_question_id = int(question_id) + 1
    if next_question_id < len(questions):
        await send_question(user_id, next_question_id)
    else:
        await show_result(user_id)
        await state.clear()


# Показ результата
async def show_result(user_id: int):
    scores = user_scores[user_id]
    max_center = max(scores, key=scores.get)
    min_center = min(scores, key=scores.get)

    # Проверяем, сбалансированы ли все три центра
    all_values = list(scores.values())
    if all(v == all_values[0] for v in all_values):
        advice_type = "balance"
    else:
        advice_type = max_center

    result_text = (
        f"🎉 \033[1mТвой результат:\033[0m\n\n"
        f"🧠 Верхний центр: {scores['top']}\n"
        f"💚 Сердечный центр: {scores['heart']}\n"
        f"🔥 Сексуальный центр: {scores['sex']}\n\n"
        # f"🔍 Доминирует: {max_center}\n"
        # f"❗ Слабый: {min_center}"
        f"{ADVICE[advice_type]}\n\n"
        
        
        f'🧭 Хочешь понять, как развить недостающие центры и притянуть настоящие отношения?\n'
        f'📲 Подпишись на канал: «Вместе» https://t.me/unionlevels  — там о любви, энергии и взрослом партнёрстве.\n\n'
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


# Запуск бота
if __name__ == "__main__":
    dp.run_polling(bot)

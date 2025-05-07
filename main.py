import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton

from questions import questions

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()


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
        f"👋 Привет {user_name}! \n\nЭто тест «Три уровня любви».\n"
        "Ответь на 9 вопросов, чтобы узнать свой доминирующий центр.",
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

    result_text = (
        f"🎉 Твой результат:\n\n"
        f"🧠 Верхний центр: {scores['top']}\n"
        f"💚 Сердечный центр: {scores['heart']}\n"
        f"🔥 Сексуальный центр: {scores['sex']}\n\n"
        f"🔍 Доминирует: {max_center}\n"
        f"❗ Слабый: {min_center}"
    )

    await bot.send_message(
        user_id,
        result_text,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="Подписаться на канал", url="https://t.me/unionlevels")
        ]])
    )


# Запуск бота
if __name__ == "__main__":
    dp.run_polling(bot)

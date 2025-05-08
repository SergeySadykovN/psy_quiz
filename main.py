import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from questions import questions

# Инициализация бота и диспетчера
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# Конфигурация Webhook
WEBHOOK_PATH = f"/webhook/{os.getenv('BOT_TOKEN')}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH

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
    waiting_for_gender = State()
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


# ========== Обработчики команд и сообщений ==========

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


@dp.message(Quiz.waiting_for_gender)
async def process_gender(message: types.Message, state: FSMContext):
    gender = message.text
    user_id = message.from_user.id

    user_data[user_id] = {
        "scores": {"top": 0, "heart": 0, "sex": 0},
        "gender": gender
    }

    await message.answer(
        f"Отлично! Теперь ответь на 9 вопросов, чтобы узнать свой доминирующий центр.",
        reply_markup=types.ReplyKeyboardRemove()
    )

    await state.set_state(Quiz.in_progress)
    await send_question(user_id, 0)


async def send_question(user_id: int, question_id: int):
    from questions import questions  # Импортируем здесь, чтобы избежать циклического импорта
    question = questions[question_id]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=opt["text"], callback_data=f"answer_{question_id}_{opt['center']}")]
        for opt in question["options"]
    ])
    await bot.send_message(user_id, question["text"], reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery, state: FSMContext):
    _, question_id, center = callback.data.split("_")
    user_id = callback.from_user.id

    user_data[user_id]["scores"][center] += 1

    next_question_id = int(question_id) + 1
    if next_question_id < len(questions):
        await send_question(user_id, next_question_id)
    else:
        await show_result(user_id)
        await state.clear()


async def show_result(user_id: int):
    data = user_data[user_id]
    scores = data["scores"]
    gender = data.get("gender", "не указан")

    max_center = max(scores, key=scores.get)
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

    admin_text = (
        f"📝 Пользователь {user_id} ({gender}) прошёл тест.\n"
        f"Результаты:\n"
        f"Верхний: {scores['top']}, Сердечный: {scores['heart']}, Сексуальный: {scores['sex']}.\n"
        f"Доминирующий центр: {advice_type.upper()}"
    )
    await bot.send_message(ADMIN_ID, admin_text)


# ========== Настройка Webhook ==========

async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook установлен на {WEBHOOK_URL}")


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    print("Webhook удален")


# Создаем aiohttp приложение
app = web.Application()
app["bot"] = bot

# Регистрируем обработчик webhook
webhook_requests_handler = SimpleRequestHandler(
    dispatcher=dp,
    bot=bot,
)
webhook_requests_handler.register(app, path=WEBHOOK_PATH)
setup_application(app, dp, bot=bot)

# ========== Запуск приложения ==========

if __name__ == "__main__":
    from aiogram.enums import ParseMode

    # Настройка бота
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Запускаем веб-сервер
    web.run_app(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),  # Render автоматически устанавливает переменную PORT
    )
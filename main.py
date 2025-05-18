import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from questions import questions
from aiogram.enums import ParseMode

# Инициализация бота и диспетчера
bot = Bot(token=os.getenv("BOT_TOKEN"), parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Конфигурация Webhook
WEBHOOK_PATH = f"/webhook/{os.getenv('BOT_TOKEN')}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH

ADMIN_ID = 966780974
CHANNEL_USERNAME = "@andbeginagain"

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
user_data = {}  # user_id: {"scores": {...}, "gender": ..., "ready": False}

# Клавиатура для выбора пола
gender_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Мужчина"), KeyboardButton(text="Женщина")]],
    resize_keyboard=True,
    one_time_keyboard=True
)

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    user_name = message.from_user.full_name
    await message.answer(
        f"👋 Привет {user_name}!\n\n"
        f"Добро пожаловать в проект 'ВМЕСТЕ'.\n"
        f"💚 Отношения становятся живыми и гармоничными, когда соединяются три центра — разум, чувства и тело.\n"
        f"🚀 Пройди короткий тест, чтобы понять, как ты выбираешь партнёра.\n\n"
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
        "gender": gender,
        "ready": False
    }

    await message.answer(
        "Отлично! Теперь ответь на 9 вопросов, чтобы узнать свой доминирующий центр.",
        reply_markup=types.ReplyKeyboardRemove()
    )

    await state.set_state(Quiz.in_progress)
    await send_question(user_id, 0)

async def send_question(user_id: int, question_id: int):
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
        await prompt_subscription(callback)
        await state.clear()

async def prompt_subscription(callback: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscription")],
        [types.InlineKeyboardButton(text="📲 Перейти в канал", url="https://t.me/andbeginagain")]
    ])
    await callback.message.answer(
        "Чтобы увидеть результат, подпишись на канал «ВМЕСТЕ»: https://t.me/andbeginagain\n"
        "После подписки нажми кнопку ниже:",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data == "check_subscription")
async def check_subscription(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            await show_result(user_id)
        else:
            await callback.message.answer("❗️Ты пока не подписан. Подпишись и попробуй снова.")
    except Exception:
        await callback.message.answer("⚠️ Не удалось проверить подписку. Попробуй позже.")

async def show_result(user_id: int):
    data = user_data[user_id]
    scores = data["scores"]
    gender = data.get("gender", "не указан")

    max_center = max(scores, key=scores.get)
    all_values = list(scores.values())
    advice_type = "balance" if all(v == all_values[0] for v in all_values) else max_center

    result_text = (
        f"🎉 Твой результат ({gender}):\n\n"
        f"🧠 Верхний центр: {scores['top']}\n"
        f"💚 Сердечный центр: {scores['heart']}\n"
        f"🔥 Сексуальный центр: {scores['sex']}\n\n"
        f"{ADVICE[advice_type]}\n\n"
        f"🧭 Хочешь развить недостающие центры? Подпишись на канал: https://t.me/unionlevels\n\n"
        f"🌿 Присоединяйся к ретриту «ВМЕСТЕ» под Петербургом — 27 июня 2025!"
    )

    await bot.send_message(
        user_id,
        result_text,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Подписаться на канал", url="https://t.me/andbeginagain")]
        ])
    )

    admin_text = (
        f"📝 Пользователь {user_id} ({gender}) прошёл тест.\n"
        f"Верхний: {scores['top']}, Сердечный: {scores['heart']}, Сексуальный: {scores['sex']}.\n"
        f"Доминирующий центр: {advice_type.upper()}"
    )
    await bot.send_message(ADMIN_ID, admin_text)

# ========== Настройка Webhook и запуск приложения ==========

async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook установлен на {WEBHOOK_URL}")

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    print("Webhook удален")

app = web.Application()
app["bot"] = bot

webhook_requests_handler = SimpleRequestHandler(
    dispatcher=dp,
    bot=bot,
)
webhook_requests_handler.register(app, path=WEBHOOK_PATH)
setup_application(app, dp, bot=bot)

if __name__ == "__main__":
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

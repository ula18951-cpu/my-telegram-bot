import logging
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command

# ВСТАВ СВІЙ ТОКЕН СЮДИ:
TOKEN = "8584377554:AAF6eRRF4t4daiCAPanx1IwJAlT_59fbkIQ"
# Твій ID вже вписаний як головний адмін:
OWNER_ID = 5506402566

# Список ID операторів підтримки (ти в ньому за замовчуванням)
# В реальному проєкті краще юзати БД, але для старту тримаємо в пам'яті
SUPPORT_TEAM = {OWNER_ID}

# Словник для збереження зв'язку: ID_повідомлення_у_підтримці -> ID_користувача
forwarded_messages = {}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- КЛАВІАТУРИ ---

def get_main_keyboard():
    kb = [
        [types.InlineKeyboardButton(text="🚀 Як почати грати", callback_data="btn_play")],
        [types.InlineKeyboardButton(text="💎 Проблеми з донатом", callback_data="btn_donate")],
        [types.InlineKeyboardButton(text="🛠️ Технічна допомога", callback_data="btn_tech")],
        [types.InlineKeyboardButton(text="🆘 Зв'язок з Адміністрацією", callback_data="btn_contact")],
        [types.InlineKeyboardButton(text="🌐 Наш сайт", url="https://ukrainelegacy.netlify.app/")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=kb)

# --- ОБРОБНИКИ КОМАНД АДМІНІСТРАЦІЇ ---

@dp.message(Command("add_support"))
async def add_support_user(message: types.Message):
    """Додає нового агента підтримки. Доступно тільки власнику."""
    if message.from_user.id != OWNER_ID:
        return
    
    try:
        # Отримуємо ID з команди (наприклад: /add_support 12345678)
        new_id = int(message.text.split()[1])
        SUPPORT_TEAM.add(new_id)
        await message.reply(f"✅ Користувача з ID `{new_id}` успішно додано до команди техпідтримки!", parse_mode="Markdown")
    except (IndexError, ValueError):
        await message.reply("❌ Неправильний формат. Використовуй:\n`/add_support ID_КОРИСТУВАЧА`", parse_mode="Markdown")

@dp.message(Command("support_list"))
async def list_support(message: types.Message):
    """Показує список усіх, хто працює в підтримці"""
    if message.from_user.id != OWNER_ID:
        return
    
    team_str = "\n".join([f"• `{uid}`" for uid in SUPPORT_TEAM])
    await message.reply(f"👥 **Поточна команда підтримки:**\n{team_str}", parse_mode="Markdown")

# --- ОБРОБНИКИ КНОПОК (МЕНЮ) ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Якщо пише адмін/саппорт
    if message.from_user.id in SUPPORT_TEAM:
        await message.reply(
            f"👋 Вітаємо в робочій панелі, {message.from_user.first_name}!\n\n"
            "Ти в команді підтримки. Коли користувачі писатимуть сюди текстові повідомлення, "
            "вони пересилатимуться тобі. Просто відповіж на повідомлення (`Reply`), щоб надіслати відповідь."
        )
        return

    # Звичайне вітання для гравців
    await message.answer(
        "👋 Вітаємо у техпідтримці Ukraine Legacy!\n\n"
        "Оберіть категорію, яка вас цікавить, або напишіть нам напряму текстовим повідомленням:",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(F.data.startswith("btn_"))
async def handle_menu_buttons(callback: types.CallbackQuery):
    action = callback.data
    
    if action == "btn_play":
        text = (
            "🚀 **Як почати грати на Ukraine Legacy:**\n\n"
            "1. Перейди на наш сайт за посиланням нижче.\n"
            "2. Завантаж наш офіційний лаунчер.\n"
            "3. Пройди реєстрацію та слідуй інструкціям на екрані!"
        )
    elif action == "btn_donate":
        text = (
            "💎 **Проблеми з донатом:**\n\n"
            "Якщо ваш платіж не пройшов або коїни не зарахувалися:\n"
            "• Надішліть сюди **скріншот чека** про оплату.\n"
            "• Вкажіть свій **ігровий нік** та сервер.\n\n"
            "Адміністратор перевірить транзакцію та вирішить проблему найближчим часом."
        )
    elif action == "btn_tech":
        text = (
            "🛠️ **Технічна допомога:**\n\n"
            "Крашить гра, не запускається лаунчер або знайшли баг?\n"
            "Опишіть проблему текстом нижче та скиньте скріншот помилки, якщо він є. "
            "Наші технічні спеціалісти дадуть вам відповідь прямо сюди."
        )
    elif action == "btn_contact":
        text = (
            "🆘 **Зв'язок з Адміністрацією:**\n\n"
            "Напишіть ваше питання або звернення одним повідомленням нижче. "
            "Воно буде миттєво передане керівництву проекту."
        )
    else:
        text = "Невідома команда."

    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# --- СИСТЕМА ТІКЕТІВ (ЗВ'ЯЗОК ТУДИ-СЮДИ) ---

@dp.message(F.chat.type == "private")
async def handle_messages(message: types.Message):
    user_id = message.from_user.id

    # 1. Якщо відповідь пише людина з підтримки
    if user_id in SUPPORT_TEAM:
        # Перевіряємо, чи це відповідь на переслане повідомлення
        if message.reply_to_message and message.reply_to_message.message_id in forwarded_messages:
            original_user_id = forwarded_messages[message.reply_to_message.message_id]
            try:
                # Копіюємо повідомлення від саппорта назад користувачу
                await message.copy_to(chat_id=original_user_id)
                await message.reply("✅ Відповідь успішно надіслана гравцю.")
            except Exception as e:
                await message.reply(f"❌ Не вдалося надіслати (можливо, бот в бані у юзера). Помилка: {e}")
        else:
            await message.reply("⚠️ Щоб відповісти користувачу, використовуй функцію `Reply` (Відповісти) на переслане повідомлення!")
        return

    # 2. Якщо пише звичайний гравець — пересилаємо всій команді підтримки
    sent_to_someone = False
    for support_id in SUPPORT_TEAM:
        try:
            # Пересилаємо повідомлення саппорту
            forwarded = await message.forward(chat_id=support_id)
            # Запам'ятовуємо, чий це тікет
            forwarded_messages[forwarded.message_id] = user_id
            sent_to_someone = True
        except Exception:
            # Якщо один з адмінів заблокував бота, просто пропускаємо його
            continue
            
    if sent_to_someone:
        await message.answer("📬 Ваше звернення надіслано підтримці. Очікуйте на відповідь прямо в цьому чаті!")
    else:
        await message.answer("⚠️ На жаль, зараз немає активних операторів онлайн. Спробуйте пізніше.")

async def main():
    print("Бот запущений та готовий до роботи підтримки!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
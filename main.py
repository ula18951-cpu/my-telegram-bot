import logging
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command

TOKEN = "ТВІЙ_ТОКЕН_БОТА"
OWNER_ID = 5506402566

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- РОБОТА З БАЗОЮ ДАНИХ (SQLite) ---
def init_db():
    conn = sqlite3.connect("support_bot.db")
    cursor = conn.cursor()
    # Таблиця для команди підтримки
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_team (
            user_id INTEGER PRIMARY KEY
        )
    """)
    # Таблиця для зв'язку повідомлень (Тікетів)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            support_msg_id INTEGER PRIMARY KEY,
            client_user_id INTEGER
        )
    """)
    # Додаємо власника за замовчуванням
    cursor.execute("INSERT OR IGNORE INTO support_team (user_id) VALUES (?)", (OWNER_ID,))
    conn.commit()
    conn.close()

def get_support_team():
    conn = sqlite3.connect("support_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM support_team")
    team = {row[0] for row in cursor.fetchall()}
    conn.close()
    return team

def add_support_to_db(user_id: int):
    conn = sqlite3.connect("support_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO support_team (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def remove_support_from_db(user_id: int):
    conn = sqlite3.connect("support_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM support_team WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def save_ticket(support_msg_id: int, client_user_id: int):
    conn = sqlite3.connect("support_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tickets (support_msg_id, client_user_id) VALUES (?, ?)", (support_msg_id, client_user_id))
    conn.commit()
    conn.close()

def get_client_by_msg(support_msg_id: int):
    conn = sqlite3.connect("support_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT client_user_id FROM tickets WHERE support_msg_id = ?", (support_msg_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

# Ініціалізуємо БД при старті
init_db()

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

# --- КОМАНДИ АДМІНІСТРАЦІЇ ---

@dp.message(Command("add_support"))
async def add_support_user(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        new_id = int(message.text.split()[1])
        add_support_to_db(new_id)
        await message.reply(f"✅ Користувача `{new_id}` додано в БД підтримки назавжди!", parse_mode="Markdown")
    except (IndexError, ValueError):
        await message.reply("❌ Формат:\n`/add_support ID`", parse_mode="Markdown")

@dp.message(Command("rem_support"))
async def remove_support_user(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        rem_id = int(message.text.split()[1])
        if rem_id == OWNER_ID:
            return await message.reply("❌ Себе видалити не можна!")
        remove_support_from_db(rem_id)
        await message.reply(f"🗑️ Користувача `{rem_id}` успішно звільнено з підтримки.", parse_mode="Markdown")
    except (IndexError, ValueError):
        await message.reply("❌ Формат:\n`/rem_support ID`", parse_mode="Markdown")

@dp.message(Command("support_list"))
async def list_support(message: types.Message):
    if message.from_user.id not in get_support_team():
        return
    team = get_support_team()
    team_str = "\n".join([f"• `{uid}`" + (" ⭐" if uid == OWNER_ID else "") for uid in team])
    await message.reply(f"👥 **Команда підтримки в базі даних:**\n{team_str}", parse_mode="Markdown")

# --- ОБРОБКА КНОПОК МЕНЮ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id in get_support_team():
        await message.reply(
            f"👋 Вітаємо в робочій панелі, {message.from_user.first_name}!\n\n"
            "База даних підключена. Чекайте на звернення гравців. Для відповіді використовуйте `Reply`."
        )
        return

    await message.answer(
        "👋 Вітаємо у техпідтримці **Ukraine Legacy**!\n\n"
        "Оберіть потрібну категорію або просто напишіть ваше питання текстом нижче:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("btn_"))
async def handle_menu_buttons(callback: types.CallbackQuery):
    action = callback.data
    texts = {
        "btn_play": "🚀 **Як почати грати:**\n\n1. Перейди на наш сайт.\n2. Завантаж офіційний лаунчер.\n3. Слідуй інструкціям!",
        "btn_donate": "💎 **Проблеми з донатом:**\n\nНадішліть сюди **скріншот чека**, ваш **ігровий нік** та сервер. Ми перевіримо все найближчим часом.",
        "btn_tech": "🛠️ **Технічна допомога:**\n\nОпишіть проблему або скиньте скріншот помилки. Наші кодери дадуть відповідь прямо сюди.",
        "btn_contact": "🆘 **Зв'язок з Адміністрацією:**\n\nНапишіть ваше звернення одним текстовим повідомленням нижче."
    }
    await callback.message.answer(texts.get(action, "Помилка"), parse_mode="Markdown")
    await callback.answer()

# --- СИСТЕМА ТІКЕТІВ З АНОНІМНІСТЮ ---

@dp.message(F.chat.type == "private")
async def handle_messages(message: types.Message):
    user_id = message.from_user.id
    team = get_support_team()

    # 1. Відповідь оператора
    if user_id in team:
        if message.reply_to_message:
            client_id = get_client_by_msg(message.reply_to_message.message_id)
            if client_id:
                try:
                    # Надсилаємо копію повідомлення гравцю анонімно
                    await message.copy_to(chat_id=client_id)
                    await message.reply("🎯 Відповідь надіслана гравцю.")
                except Exception as e:
                    await message.reply(f"❌ Помилка відправки: {e}")
            else:
                await message.reply("⚠️ Не вдалося знайти автора цього тікету в базі даних.")
        else:
            await message.reply("⚠️ Використовуй кнопку `Reply` (Відповісти) на картку тікету!")
        return

    # 2. Звернення від гравця
    for support_id in team:
        try:
            # Спочатку надсилаємо красиву інфо-картку про гравця
            await bot.send_message(
                chat_id=support_id,
                text=f"📥 **Нове звернення!**\n\n"
                     f"👤 **Гравець:** {message.from_user.mention_html()}\n"
                     f"🆔 **ID:** <code>{user_id}</code>\n"
                     f"✍️ **Повідомлення нижче:**",
                parse_mode="HTML"
            )
            # Пересилаємо саме повідомлення або скріншот
            user_msg = await message.copy_to(chat_id=support_id)
            
            # Прив'язуємо копію повідомлення до ID клієнта в БД
            save_ticket(user_msg.message_id, user_id)
            
        except Exception:
            continue

    await message.answer("📬 Ваше повідомлення передано команді підтримки Ukraine Legacy!")

# --- ЗАПУСК БОТА ---
async def main():
    print("Бот підтримки [SQLite + Анонімність] успішно запущений!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

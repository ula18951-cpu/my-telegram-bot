import logging
import asyncio
import sqlite3
import time
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command

TOKEN = "8584377554:AAF6eRRF4t4daiCAPanx1IwJAlT_59fbkIQ"
OWNER_ID = 5506402566

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

last_message_time = {}
ANTI_SPAM_DELAY = 3.0

# --- РОБОТА З БАЗОЮ ДАНИХ (SQLite) ---
def init_db():
    conn = sqlite3.connect("support_bot.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS support_team (user_id INTEGER PRIMARY KEY)")
    # Додали поле operator_msg_id для відстеження картки, яку треба буде редагувати
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            support_msg_id INTEGER PRIMARY KEY,
            client_user_id INTEGER,
            operator_msg_id INTEGER DEFAULT 0
        )
    """)
    cursor.execute("CREATE TABLE IF NOT EXISTS blacklist (user_id INTEGER PRIMARY KEY)")
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

def save_ticket(support_msg_id: int, client_user_id: int, operator_msg_id: int):
    conn = sqlite3.connect("support_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tickets (support_msg_id, client_user_id, operator_msg_id) VALUES (?, ?, ?)", 
                   (support_msg_id, client_user_id, operator_msg_id))
    conn.commit()
    conn.close()

def get_client_by_msg(support_msg_id: int):
    conn = sqlite3.connect("support_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT client_user_id FROM tickets WHERE support_msg_id = ?", (support_msg_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def delete_ticket_from_db(client_user_id: int):
    conn = sqlite3.connect("support_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tickets WHERE client_user_id = ?", (client_user_id,))
    conn.commit()
    conn.close()

def ban_user_in_db(user_id: int):
    conn = sqlite3.connect("support_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO blacklist (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def unban_user_in_db(user_id: int):
    conn = sqlite3.connect("support_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blacklist WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_user_banned(user_id: int) -> bool:
    conn = sqlite3.connect("support_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM blacklist WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

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

def get_take_ticket_keyboard(client_id: int):
    kb = [[types.InlineKeyboardButton(text="🛠️ Взяти тікет в роботу", callback_data=f"take_{client_id}")]]
    return types.InlineKeyboardMarkup(inline_keyboard=kb)

def get_close_ticket_keyboard(client_id: int):
    kb = [[types.InlineKeyboardButton(text="❌ Закрити тікет", callback_data=f"close_{client_id}")]]
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

@dp.message(Command("ban_user"))
async def ban_user_cmd(message: types.Message):
    if message.from_user.id not in get_support_team():
        return
    try:
        b_id = int(message.text.split()[1])
        if b_id in get_support_team():
            return await message.reply("❌ Не можна забанити адміна!")
        ban_user_in_db(b_id)
        delete_ticket_from_db(b_id)
        await message.reply(f"🚫 Гравця `{b_id}` успішно забанено.", parse_mode="Markdown")
    except (IndexError, ValueError):
        await message.reply("❌ Формат:\n`/ban_user ID`", parse_mode="Markdown")

@dp.message(Command("unban_user"))
async def unban_user_cmd(message: types.Message):
    if message.from_user.id not in get_support_team():
        return
    try:
        b_id = int(message.text.split()[1])
        unban_user_in_db(b_id)
        await message.reply(f"🟢 Гравця `{b_id}` успішно розбанено.", parse_mode="Markdown")
    except (IndexError, ValueError):
        await message.reply("❌ Формат:\n`/unban_user ID`", parse_mode="Markdown")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if is_user_banned(message.from_user.id):
        return
        
    if message.from_user.id in get_support_team():
        await message.reply(f"👋 Вітаємо в робочій панелі, {message.from_user.first_name}!\nСистема розподілу тікетів активована.")
        return

    await message.answer(
        "👋 Вітаємо у техпідтримці **Ukraine Legacy**!\n\nОберіть потрібну категорію або просто напишіть ваше питання текстом нижче:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("btn_"))
async def handle_menu_buttons(callback: types.CallbackQuery):
    if is_user_banned(callback.from_user.id):
        return await callback.answer("🚨 Ви заблоковані!", show_alert=True)
    
    action = callback.data
    texts = {
        "btn_play": "🚀 **Як почати грати:**\n\n1. Перейди на наш сайт.\n2. Завантаж офіційний лаунчер.\n3. Слідуй інструкціям!",
        "btn_donate": "💎 **Проблеми з донатом:**\n\nНадішліть сюди **скріншот чека**, ваш **ігровий нік** та сервер. Ми перевіримо все найближчим часом.",
        "btn_tech": "🛠️ **Технічна допомога:**\n\nОпишіть проблему або скиньте скріншот помилки. Наші кодери дадуть відповідь прямо сюди.",
        "btn_contact": "🆘 **Зв'язок з Адміністрацією:**\n\nНапишіть ваше звернення одним текстовим повідомленням нижче."
    }
    await callback.message.answer(texts.get(action, "Помилка"), parse_mode="Markdown")
    await callback.answer()

# --- ОБРОБКА ПІДКЛЮЧЕННЯ ОПЕРАТОРА (ВЗЯТИ ТІКЕТ) ---

@dp.callback_query(F.data.startswith("take_"))
async def handle_take_ticket(callback: types.CallbackQuery):
    team = get_support_team()
    if callback.from_user.id not in team:
        return await callback.answer("❌ Ви не є агентом підтримки!", show_alert=True)

    client_id = int(callback.data.split("_")[1])
    
    # Отримуємо ім'я та прізвище адміна з Телеграму
    first_name = callback.from_user.first_name
    last_name = callback.from_user.last_name if callback.from_user.last_name else ""
    full_name = f"{first_name} {last_name}".strip()

    # Сповіщаємо гравця гарним повідомленням
    try:
        await bot.send_message(
            chat_id=client_id,
            text=f"🎧 **Оператор {full_name} підключився до вашого тікету.**\n\n"
                 f"Вітаю, мене звати {first_name}, чим я можу Вам допомогти?",
            parse_mode="Markdown"
        )
    except Exception:
        pass

    # Оновлюємо картку у адмінів — міняємо кнопку на "Закрити тікет"
    await callback.message.edit_reply_markup(reply_markup=get_close_ticket_keyboard(client_id))
    await callback.answer(f"✅ Ви взяли тікет в роботу!")

# --- ОБРОБКА ЗАКРИТТЯ ТІКЕТУ ---

@dp.callback_query(F.data.startswith("close_"))
async def handle_close_ticket_btn(callback: types.CallbackQuery):
    team = get_support_team()
    if callback.from_user.id not in team:
        return await callback.answer("❌ Ви не є агентом підтримки!", show_alert=True)

    client_id = int(callback.data.split("_")[1])
    try:
        await bot.send_message(
            chat_id=client_id,
            text="🔒 **Ваш тікет було закрито адміністратором.**\nДякуємо за звернення!",
            parse_mode="Markdown"
        )
    except Exception:
        pass

    delete_ticket_from_db(client_id)
    await callback.message.edit_text(
        text=f"{callback.message.text}\n\n🛑 **Тікет закрито адміном {callback.from_user.first_name}**",
        reply_markup=None
    )
    await callback.answer("✅ Тікет закритий!")

# --- СИСТЕМА ТІКЕТІВ ---

@dp.message(F.chat.type == "private")
async def handle_messages(message: types.Message):
    user_id = message.from_user.id
    team = get_support_team()

    if is_user_banned(user_id):
        return

    # 1. Робота оператора
    if user_id in team:
        if message.reply_to_message:
            client_id = get_client_by_msg(message.reply_to_message.message_id)
            if client_id:
                if message.text and message.text.strip() == "/close":
                    try:
                        await bot.send_message(chat_id=client_id, text="🔒 **Ваш тікет було закрито адміністратором.**", parse_mode="Markdown")
                    except Exception:
                        pass
                    delete_ticket_from_db(client_id)
                    await message.reply("🛑 Тікет успішно закрито командою.")
                    return
                
                try:
                    await message.copy_to(chat_id=client_id)
                    await message.reply("🎯 Відповідь надіслана гравцю.")
                except Exception as e:
                    await message.reply(f"❌ Помилка відправки: {e}")
            else:
                await message.reply("⚠️ Тікет не знайдено або вже закритий.")
        else:
            await message.reply("⚠️ Використовуй кнопку `Reply` для відповіді!")
        return

    # 2. Анти-спам
    current_time = time.time()
    if user_id in last_message_time:
        if current_time - last_message_time[user_id] < ANTI_SPAM_DELAY:
            return
    last_message_time[user_id] = current_time

    # 3. Пересилка звернення
    for support_id in team:
        try:
            # Інфо-картка
            op_card = await bot.send_message(
                chat_id=support_id,
                text=f"📥 **Нове звернення!**\n\n"
                     f"👤 **Гравець:** {message.from_user.mention_html()}\n"
                     f"🆔 **ID:** <code>{user_id}</code>\n"
                     f"✍️ **Повідомлення нижче:**",
                parse_mode="HTML"
            )
            # Питання з кнопкою "Взяти в роботу"
            user_msg = await message.copy_to(
                chat_id=support_id,
                reply_markup=get_take_ticket_keyboard(user_id)
            )
            # Зберігаємо зв'язок повідомлень
            save_ticket(user_msg.message_id, user_id, op_card.message_id)
        except Exception:
            continue

    await message.answer("📬 Ваше повідомлення передано команді підтримки Ukraine Legacy! Очікуйте підключення оператора.")

# --- ЗАПУСК БОТА ---
async def main():
    print("Бот підтримки [Система операторів + Анти-спам] успішно запущений!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

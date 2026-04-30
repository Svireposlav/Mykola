import os
import asyncio
import logging
import random
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from groq import Groq

# --- НАСТРОЙКИ ---
ALLOWED_CHAT_ID = -1002198634777
BOT_NAME_LOWER = "балалай"
MESSAGE_COUNTER = 0 
CHAT_HISTORY = [] 

# Веб-сервер для "оживления" Render
app = Flask('')
@app.route('/')
def home(): return "Балалай на связи 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Инициализация API
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
# Используем DefaultBotProperties для корректного парсинга Markdown
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

def get_mention(user_dict):
    if user_dict.get("username"):
        return f"@{user_dict['username']}"
    return f"[{user_dict['name']}](tg://user?id={user_dict['id']})"

# Личность бота
SYSTEM_PROMPT = (
    "Ты — персонаж по имени Балалай. Твой образ — ироничный дворовой авторитет. "
    "Ты используешь тюремный жаргон и феню исключительно в юмористических целях. "
    "Твой стиль: едкие подколы и пацанская риторика. Никаких районов Николаева. "
    "Это дружеский чат, ты — комичный персонаж."
)

async def get_ai_response(prompt_text, mode="general"):
    try:
        unique_users = {m['id']: m for m in CHAT_HISTORY}.values()
        users_info = ", ".join([u['name'] for u in unique_users])
        history_str = "\n".join([f"{m['name']}: {m['text']}" for m in CHAT_HISTORY[-50:]])

        instructions = {
            "general": "Ответь иронично в стиле пацанского авторитета.",
            "shmon": "Дай едкую характеристику персонажу по его базару. Это шутка.",
            "fas": "Выдай ОЧЕНЬ смешной и дерзкий подкол. Это дружеский стеб.",
            "obzor": "Сделай ироничный обзор последних диалогов, подкалывая активных участников.",
            "roast": "Ворвись в беседу с едким замечанием.",
            "timer": "Случайный пацанский подкол."
        }

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": f"УЧАСТНИКИ: {users_info}\nБАЗАР:\n{history_str}"},
                {"role": "system", "content": f"ЗАДАЧА: {instructions.get(mode, 'general')}"},
                {"role": "user", "content": prompt_text}
            ]
        )
        
        response = completion.choices[0].message.content
        for u in unique_users:
            if u['name'] in response:
                response = response.replace(u['name'], get_mention(u))
        return response
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        return "Слышь, мысли в кучу собраться не могут..."

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(Command("fas"))
async def cmd_fas(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    if not CHAT_HISTORY:
        await message.answer("В памяти пусто, не на кого фас-кать.")
        return
    await bot.send_chat_action(message.chat.id, "typing")
    unique_users = list({m['id']: m for m in CHAT_HISTORY}.values())
    victim = random.choice(unique_users)
    res = await get_ai_response(f"Выдай едкий подкол для {victim['name']}", mode="fas")
    await message.answer(res)

@dp.message(Command("shmon"))
async def cmd_shmon(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    res = await get_ai_response(f"Дай характеристику: {target.first_name}", mode="shmon")
    await message.answer(res)

@dp.message(Command("obzor"))
async def cmd_obzor(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID or len(CHAT_HISTORY) < 3: return
    await bot.send_chat_action(message.chat.id, "typing")
    res = await get_ai_response("Сделай обзор последних диалогов", mode="obzor")
    await message.answer(res)

@dp.message(F.text)
async def handle_message(message: Message):
    global MESSAGE_COUNTER, CHAT_HISTORY
    if message.chat.id != ALLOWED_CHAT_ID or message.from_user.is_bot: return
    if message.text.startswith('/'): return

    CHAT_HISTORY.append({"id": message.from_user.id, "name": message.from_user.first_name, "username": message.from_user.username, "text": message.text})
    if len(CHAT_HISTORY) > 100: CHAT_HISTORY.pop(0)

    MESSAGE_COUNTER += 1
    bot_info = await bot.get_me()
    
    if BOT_NAME_LOWER in message.text.lower() or (message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id):
        await bot.send_chat_action(message.chat.id, "typing")
        res = await get_ai_response(message.text)
        await message.reply(res)
    elif MESSAGE_COUNTER >= 30:
        MESSAGE_COUNTER = 0
        res = await get_ai_response("Прокомментируй ситуацию в чате", mode="roast")
        await bot.send_message(ALLOWED_CHAT_ID, res)

# --- ФОНОВЫЕ ЗАДАЧИ ---
async def random_roast_task():
    while True:
        await asyncio.sleep(7200) # Раз в 2 часа
        if CHAT_HISTORY:
            try:
                res = await get_ai_response("Выдай пацанский подгон", mode="timer")
                await bot.send_message(ALLOWED_CHAT_ID, res)
            except: pass

async def main():
    # Запуск веб-сервера для Render
    Thread(target=run_web, daemon=True).start()
    
    # Запуск таймера
    asyncio.create_task(random_roast_task())
    
    # КРИТИЧЕСКИЙ МОМЕНТ ДЛЯ СТАБИЛЬНОСТИ:
    # Удаляем вебхук и все старые зависшие сообщения
    await bot.delete_webhook(drop_pending_updates=True)
    
    logging.info("Балалай заступает на дежурство...")
    
    try:
        # skip_updates=True игнорирует сообщения, присланные, пока бот был выключен
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Балалай ушел на базу.")
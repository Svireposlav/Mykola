import os
import asyncio
import logging
import random
import time
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
CHAT_HISTORY = [] 

# Веб-сервер для удержания жизни (Пингатор)
app = Flask('')

@app.route('/')
def home():
    return "Балалай на стрёме! Статус: ONLINE"

@app.route('/ping')
def ping():
    return "PONG", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

async def get_ai_response(prompt_text, mode="general"):
    try:
        current_time = time.time()
        recent_history = [m for m in CHAT_HISTORY if current_time - m['time'] < 28800]
        history_str = "\n".join([f"{m['name']}: {m['text']}" for m in recent_history[-30:]])

        instructions = {
            "general": "Ответь едко в стиле пацанского авторитета.",
            "shmon": "Дай жесткую характеристику персонажу. Шути на грани.",
            "fas": "Выдай ОЧЕНЬ ядовитый и дерзкий подкол.",
            "hourly_roast": "Выбери фразу участника и дерзко докопайся до неё.",
            "chizl_target": "Наглая предъява @Chizlmynizl за молчание. Почему он завалил хлебало?"
        }

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Ты — Балалай, дерзкий авторитет. Ты жестко стебёшь. Феня, сарказм, агрессивно-ироничный стиль. Никаких районов."},
                {"role": "user", "content": f"БАЗАР ЗА 8 ЧАСОВ:\n{history_str}\n\nЗАДАЧА: {instructions.get(mode, 'general')}\nКОНТЕКСТ: {prompt_text}"}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        return "Слышь, че-то связь с космосом барахлит..."

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(Command("fas"))
async def cmd_fas(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    await bot.send_chat_action(message.chat.id, "typing")
    victim = random.choice(CHAT_HISTORY) if CHAT_HISTORY else {"name": "фраер"}
    res = await get_ai_response(f"Уничтожь подколом: {victim['name']}", mode="fas")
    await message.answer(res)

@dp.message(Command("shmon"))
async def cmd_shmon(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    await bot.send_chat_action(message.chat.id, "typing")
    res = await get_ai_response(f"Раскидай по фактам за этого типа: {target.first_name}", mode="shmon")
    await message.answer(res)

# --- ТАЙМЕРЫ ---

async def hourly_worker():
    while True:
        await asyncio.sleep(3600)
        current_time = time.time()
        active_victims = [m for m in CHAT_HISTORY if current_time - m['time'] < 28800]
        if active_victims:
            target_msg = random.choice(active_victims)
            res = await get_ai_response(f"Прицепись к фразе: '{target_msg['text']}'", mode="hourly_roast")
            try:
                await bot.send_message(ALLOWED_CHAT_ID, res, reply_to_message_id=target_msg['msg_id'])
            except:
                await bot.send_message(ALLOWED_CHAT_ID, res)

async def chizl_worker():
    while True:
        await asyncio.sleep(7200)
        res = await get_ai_response("Наедь на @Chizlmynizl за молчание", mode="chizl_target")
        await bot.send_message(ALLOWED_CHAT_ID, res)

# --- ГЛАВНЫЙ ОБРАБОТЧИК ---

@dp.message(F.text)
async def handle_message(message: Message):
    global CHAT_HISTORY
    if message.chat.id != ALLOWED_CHAT_ID or message.from_user.is_bot: return

    if not message.text.startswith('/'):
        CHAT_HISTORY.append({
            "id": message.from_user.id,
            "name": message.from_user.first_name,
            "text": message.text,
            "time": time.time(),
            "msg_id": message.message_id
        })
        if len(CHAT_HISTORY) > 200: CHAT_HISTORY.pop(0)

    bot_info = await bot.get_me()
    is_called = BOT_NAME_LOWER in message.text.lower()
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id

    if is_called or is_reply:
        await bot.send_chat_action(message.chat.id, "typing")
        res = await get_ai_response(message.text)
        await message.reply(res)

async def main():
    # Запуск Flask в отдельном потоке
    server_thread = Thread(target=run_web, daemon=True)
    server_thread.start()
    
    # Запуск фоновых задач
    asyncio.create_task(hourly_worker())
    asyncio.create_task(chizl_worker())
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("--- БАЛАЛАЙ ПОД ПРИСМОТРОМ РОБОТОВ ---")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
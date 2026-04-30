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
# Временно убираем жесткую проверку, чтобы понять, видит ли бот хоть что-то
ALLOWED_CHAT_ID = -1002198634777 
BOT_NAME_LOWER = "балалай"
MESSAGE_COUNTER = 0 
CHAT_HISTORY = [] 

app = Flask('')
@app.route('/')
def home(): return "Бот в сети!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

# --- ФУНКЦИИ ---
def get_mention(user_dict):
    if user_dict.get("username"):
        return f"@{user_dict['username']}"
    return f"[{user_dict['name']}](tg://user?id={user_dict['id']})"

async def get_ai_response(prompt_text, mode="general"):
    try:
        unique_users = {m['id']: m for m in CHAT_HISTORY}.values()
        users_info = ", ".join([u['name'] for u in unique_users])
        history_str = "\n".join([f"{m['name']}: {m['text']}" for m in CHAT_HISTORY[-50:]])

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Ты Балалай, дерзкий авторитет. Твой стиль — феня и сарказм. Никаких районов."},
                {"role": "user", "content": f"Участники: {users_info}\nИстория: {history_str}\nЗадача: {mode}\nКонтекст: {prompt_text}"}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        return "Связь оборвалась..."

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("fas"))
async def cmd_fas(message: Message):
    # ПЕЧАТЬ В ЛОГИ ПРИ ЛЮБОМ РАСКЛАДЕ
    print(f"!!! ПОЛУЧЕНА КОМАНДА /FAS ОТ {message.from_user.id} !!!")
    if not CHAT_HISTORY:
        await message.answer("Пусто в памяти.")
        return
    victim = random.choice(list({m['id']: m for m in CHAT_HISTORY}.values()))
    res = await get_ai_response(f"Подколи {victim['name']}", mode="fas")
    await message.answer(res)

@dp.message(F.text)
async def handle_message(message: Message):
    global MESSAGE_COUNTER, CHAT_HISTORY
    
    # ЭТО ПОЯВИТСЯ В ЛОГАХ RENDER ЕСЛИ БОТ ХОТЬ ЧТО-ТО ВИДИТ
    print(f"!!! ЛОГ СООБЩЕНИЯ: {message.from_user.first_name} написал: {message.text} (Chat ID: {message.chat.id})")

    # Если ID не совпадает, бот просто напишет в логи правильный ID, но не ответит
    if message.chat.id != ALLOWED_CHAT_ID:
        print(f"Внимание! Сообщение из левого чата. ID этого чата: {message.chat.id}")
        return

    CHAT_HISTORY.append({"id": message.from_user.id, "name": message.from_user.first_name, "username": message.from_user.username, "text": message.text})
    if len(CHAT_HISTORY) > 100: CHAT_HISTORY.pop(0)

    if BOT_NAME_LOWER in message.text.lower():
        res = await get_ai_response(message.text)
        await message.reply(res)

# --- ЗАПУСК ---

async def main():
    Thread(target=run_web, daemon=True).start()
    
    # ЖЕСТКИЙ СБРОС ВЕБХУКА
    print("Удаляю вебхуки...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    print("Запускаю polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
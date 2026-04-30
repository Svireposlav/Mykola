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
# ВАЖНО: Число без пробелов и лишних символов
ALLOWED_CHAT_ID = -1002198634777
BOT_NAME_LOWER = "балалай"
CHAT_HISTORY = []

app = Flask('')
@app.route('/')
def home(): return "Бот на базе!"

def run_web():
    # Render требует привязки к 0.0.0.0
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

async def get_ai_response(prompt_text, mode="general"):
    try:
        unique_users = {m['id']: m for m in CHAT_HISTORY}.values()
        users_info = ", ".join([u['name'] for u in unique_users])
        history_str = "\n".join([f"{m['name']}: {m['text']}" for m in CHAT_HISTORY[-20:]])

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Ты Балалай, дерзкий авторитет. Твой стиль — феня и сарказм. Никаких районов Николаева."},
                {"role": "user", "content": f"Участники: {users_info}\nИстория: {history_str}\nЗадача: {mode}\nКонтекст: {prompt_text}"}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        return "Связь оборвалась, фраера..."

# --- ОБРАБОТЧИКИ (ПОРЯДОК ВАЖЕН) ---

@dp.message(Command("fas"))
async def cmd_fas(message: Message):
    # Лог сразу в консоль Render
    print(f"!!! КОМАНДА /FAS В ЧАТЕ {message.chat.id} !!!")
    
    if message.chat.id != ALLOWED_CHAT_ID:
        print(f"Отказ: ID {message.chat.id} не совпадает с {ALLOWED_CHAT_ID}")
        return

    if not CHAT_HISTORY:
        await message.answer("В памяти пусто, не на кого гавкать.")
        return

    await bot.send_chat_action(message.chat.id, "typing")
    victim = random.choice(list({m['id']: m for m in CHAT_HISTORY}.values()))
    res = await get_ai_response(f"Подколи этого персонажа: {victim['name']}", mode="fas")
    await message.answer(res)

@dp.message(F.text)
async def handle_message(message: Message):
    global CHAT_HISTORY
    
    # Видит ли бот сообщение вообще?
    print(f"Входящее от {message.from_user.first_name} (ID: {message.chat.id}): {message.text[:30]}")

    if message.chat.id != ALLOWED_CHAT_ID:
        return

    if message.from_user.is_bot:
        return

    # Добавляем в историю
    CHAT_HISTORY.append({
        "id": message.from_user.id, 
        "name": message.from_user.first_name, 
        "text": message.text
    })
    if len(CHAT_HISTORY) > 50: CHAT_HISTORY.pop(0)

    # Ответ на имя или реплику
    is_called = BOT_NAME_LOWER in message.text.lower()
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == (await bot.get_me()).id

    if is_called or is_reply:
        await bot.send_chat_action(message.chat.id, "typing")
        res = await get_ai_response(message.text)
        await message.reply(res)

# --- ЗАПУСК ---

async def main():
    # Запуск веб-сервера
    Thread(target=run_web, daemon=True).start()
    
    # Сброс вебхука и старых сообщений
    await bot.delete_webhook(drop_pending_updates=True)
    
    print("--- БАЛАЛАЙ ЗАПУЩЕН ---")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
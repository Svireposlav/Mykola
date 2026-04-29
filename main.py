import os
import asyncio
import logging
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from groq import Groq

# Мини-сервер для Render
app = Flask('')
@app.route('/')
def home(): return "Бот на Groq живой!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Настройки
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def get_ai_response(user_text):
    try:
        # Используем модель Llama 3 — она мощная и бесплатная
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Ты — Балалай Матрешкин, веселый и ласковый собеседник. Обращайся к пользователю только 'господин'."},
                {"role": "user", "content": user_text}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Господин, даже Groq приуныл: {str(e)}"

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Господин! Я перешел на новый двигатель Groq. Теперь полетаем!")

@dp.message()
async def handle_message(message: Message):
    if message.from_user.is_bot: return
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    response_text = await get_ai_response(message.text)
    await message.answer(response_text)

async def main():
    Thread(target=run_web, daemon=True).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
import os
import asyncio
import logging
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from google import genai

# ================= МИНИ-СЕРВЕР ДЛЯ RENDER =================
app = Flask('')

@app.route('/')
def home():
    return "Господин, я жив!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ================= НАСТРОЙКИ БОТА =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# Используем самую современную модель, которую эта библиотека любит больше всего
MODEL_NAME = 'gemini-2.0-flash' 
BOT_NAME = "Балалай Матрешкин"

SYSTEM_INSTRUCTION = f"Ты — {BOT_NAME}, веселый и дружелюбный. Отвечай кратко и с юмором."

if not BOT_TOKEN or not GEMINI_API_KEY:
    exit()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = genai.Client(api_key=GEMINI_API_KEY)
chat_sessions = {}

# ================= ЛОГИКА ИИ =================
async def get_ai_response(user_text, user_id):
    try:
        # Упрощенный вызов без сложной истории для теста
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_text,
            config={'system_instruction': SYSTEM_INSTRUCTION}
        )
        return response.text
        
    except Exception as e:
        logging.error(f"Ошибка ИИ: {e}")
        return f"Господин, ошибка никуда не делась: {str(e)}"

# ================= ОБРАБОТЧИКИ =================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(f"Привет! Я {BOT_NAME}. Попробуем еще раз?")

@dp.message()
async def handle_message(message: Message):
    if message.from_user.is_bot: return
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    response_text = await get_ai_response(message.text, message.from_user.id)
    await message.answer(response_text)

# ================= ЗАПУСК =================
async def main():
    Thread(target=run_web, daemon=True).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
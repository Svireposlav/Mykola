import os
import asyncio
import logging
from threading import Thread
from flask import Flask
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message

# ================= МИНИ-СЕРВЕР =================
app = Flask('')
@app.route('/')
def home(): return "Бот живой!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Настраиваем ИИ старым надежным способом
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================= ЛОГИКА =================
async def get_ai_response(user_text):
    try:
        # Старый добрый метод генерации
        response = model.generate_content(user_text)
        return response.text
    except Exception as e:
        return f"Господин, даже старый метод выдает ошибку: {str(e)}"

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Я Балалай. Попытка №1000, поехали!")

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
    asyncio.run(main())
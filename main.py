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
    return "Господин, я жив и работаю!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ================= НАСТРОЙКИ БОТА =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = 'models/gemini-1.5-flash'
BOT_NAME = "Балалай Матрешкин"

SYSTEM_INSTRUCTION = f"""
Ты — {BOT_NAME}, веселый, эрудированный и дружелюбный участник чата.
Твоя цель — общаться с людьми как реальный человек.
"""

if not BOT_TOKEN or not GEMINI_API_KEY:
    print("ОШИБКА: Ключи не найдены!")
    exit()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = genai.Client(api_key=GEMINI_API_KEY)
chat_sessions = {}

# ================= ЛОГИКА ИИ =================
async def get_ai_response(user_text, user_id):
    if user_id not in chat_sessions:
        chat_sessions[user_id] = []
    
    history = [{"role": "user", "parts": [{"text": f"ИНСТРУКЦИЯ: {SYSTEM_INSTRUCTION}"}]}]
    history.extend(chat_sessions[user_id])
    history.append({"role": "user", "parts": [{"text": user_text}]})
    
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=history
        )
        
        answer = response.text
        chat_sessions[user_id].append({"role": "user", "parts": [{"text": user_text}]})
        chat_sessions[user_id].append({"role": "model", "parts": [{"text": answer}]})
        
        if len(chat_sessions[user_id]) > 10:
            chat_sessions[user_id] = chat_sessions[user_id][-10:]
            
        return answer
        
    except Exception as e:
        logging.error(f"Ошибка ИИ: {e}")
        # ВОТ ЭТА ПРАВКА: Бот пришлет саму ошибку прямо в Telegram
        return f"Господин, случилась беда с ИИ: {str(e)}"

# ================= ОБРАБОТЧИКИ =================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(f"Привет! 👋 Я {BOT_NAME}. Напиши мне что-нибудь!")

@dp.message()
async def handle_message(message: Message):
    if message.from_user.is_bot:
        return
    
    try:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        response_text = await get_ai_response(message.text, message.from_user.id)
        await message.answer(response_text)
    except Exception as e:
        logging.error(f"Ошибка: {e}")

# ================= ЗАПУСК =================
async def main():
    server_thread = Thread(target=run_web)
    server_thread.daemon = True
    server_thread.start()
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Стоп.")
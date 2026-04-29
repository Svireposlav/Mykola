import os 
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
import google.generativeai as genai # Старая, но рабочая библиотека

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

BOT_NAME = "Балалай Матрешкин"

SYSTEM_INSTRUCTION = f"""
Ты — {BOT_NAME}, веселый, эрудированный и дружелюбный участник чата.
Общайся как реальный человек, шути, поддерживай беседу. Не говори, что ты ИИ.
"""

if BOT_TOKEN == "СЮДА_ВСТАВИТЬ_ТОКЕН_ОТ_BOTFATHER" or GEMINI_API_KEY == "СЮДА_ВСТАВИТЬ_КЛЮЧ_GOOGLE":
    print("ОШИБКА: Вставьте ключи!")
    exit()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Настройка старой библиотеки
genai.configure(api_key=GEMINI_API_KEY)

# Используем модель, которая точно доступна в старой библиотеке
# Попробуем 'gemini-1.5-flash-latest' или просто 'gemini-1.5-flash'
model_name = 'models/gemini-flash-latest' 
model = genai.GenerativeModel(model_name, system_instruction=SYSTEM_INSTRUCTION)

chat_sessions = {}

async def get_ai_response(user_text, user_id):
    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[])
    
    session = chat_sessions[user_id]
    try:
        # Отправка сообщения
        response = await asyncio.to_thread(session.send_message, user_text)
        return response.text
    except Exception as e:
        logging.error(f"Ошибка ИИ: {e}")
        return "Ой, я задумался... Попробуй позже!"

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(f"Привет! 👋 Я {BOT_NAME}. Готов болтать!")

@dp.message()
async def handle_message(message: Message):
    if message.from_user.is_bot: return
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    user_name = message.from_user.first_name
    prompt = f"{user_name}: {message.text}"
    response_text = await get_ai_response(prompt, message.from_user.id)
    await message.answer(response_text)

async def main():
    print(f"Бот {BOT_NAME} запущен (старая библиотека)...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен.")
import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from google import genai  # <-- НОВАЯ БИБЛИОТЕКА

# ================= НАСТРОЙКИ =================
# Ключи берутся из переменных окружения Render
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Модель (используем ту, что точно работает)
MODEL_NAME = 'models/gemini-flash-latest' 

BOT_NAME = "Балалай Матрешкин"

SYSTEM_INSTRUCTION = f"""
Ты — {BOT_NAME}, веселый, эрудированный и дружелюбный участник чата.
Твоя цель — общаться с людьми как реальный человек, шутить, поддерживать беседу на любые темы.
Ты не робот. Избегай официальных фраз. Отвечай кратко, с юмором.
Никогда не говори, что ты ИИ. Просто будь собой.
"""

if not BOT_TOKEN or not GEMINI_API_KEY:
    print("ОШИБКА: Не найдены ключи BOT_TOKEN или GEMINI_API_KEY!")
    exit()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация клиента НОВОЙ библиотеки
client = genai.Client(api_key=GEMINI_API_KEY)

chat_sessions = {}

async def get_ai_response(user_text, user_id):
    if user_id not in chat_sessions:
        chat_sessions[user_id] = []
    
    # Формируем историю с системной инструкцией
    history = [{"role": "system", "parts": [{"text": SYSTEM_INSTRUCTION}]}]
    history.extend(chat_sessions[user_id])
    history.append({"role": "user", "parts": [{"text": user_text}]})
    
    try:
        # Вызов модели через новый SDK
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=history
        )
        
        answer = response.text
        
        # Сохраняем диалог
        chat_sessions[user_id].append({"role": "user", "parts": [{"text": user_text}]})
        chat_sessions[user_id].append({"role": "model", "parts": [{"text": answer}]})
        
        # Очистка старой истории (оставляем последние 20 сообщений)
        if len(chat_sessions[user_id]) > 20:
            chat_sessions[user_id] = chat_sessions[user_id][-20:]
            
        return answer
        
    except Exception as e:
        logging.error(f"Ошибка ИИ: {e}")
        return "Ой, я немного задумался... Попробуй еще раз!"

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(f"Привет! 👋 Я {BOT_NAME}. Готов болтать и шутить!")

@dp.message()
async def handle_message(message: Message):
    if message.from_user.is_bot:
        return
    
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    user_name = message.from_user.first_name
    prompt = f"{user_name}: {message.text}"
    
    response_text = await get_ai_response(prompt, message.from_user.id)
    await message.answer(response_text)

async def main():
    print(f"Бот {BOT_NAME} запущен с моделью {MODEL_NAME}...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен.")
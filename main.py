import os
import asyncio
import logging
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from groq import Groq

# Мини-сервер для Render
app = Flask('')
@app.route('/')
def home(): return "Дерзкий Балалай в строю!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Настройки
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def get_ai_response(user_text, user_name):
    try:
        # УСТАНОВКА ХАРАКТЕРА: Чистый яд и сарказм без лишних упоминаний
        instruction = (
            f"Ты — Балалай Матрешкин, мастер черного юмора. Общаешься с {user_name}. "
            "Твоя задача: отвечать дерзко, цинично и с издевкой. Используй жесткий сарказм. "
            "НЕ упоминай Штурмослава, если тебя не спросят о нем. "
            "Веди себя как самый умный в этом чате, стебись над глупостью собеседника."
        )
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": user_text}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Тут даже мои микросхемы охренели от такой тупости... (Ошибка: {str(e)})"

@dp.message(CommandStart())
async def cmd_start(message: Message):
    name = message.from_user.first_name
    await message.answer(f"Ну здорово, {name}. Я Балалай, и теперь я буду наводить тут шороху. Не плачь только потом.")

@dp.message(F.text)
async def handle_message(message: Message):
    if message.from_user.is_bot: return
    
    # Получаем имя того, кто пишет
    user_name = message.from_user.first_name
    
    # Включаем имитацию печатания
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    response_text = await get_ai_response(message.text, user_name)
    await message.reply(response_text) # Отвечаем именно реплаем (ответом на сообщение)

async def main():
    Thread(target=run_web, daemon=True).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
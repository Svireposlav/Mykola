import os
import asyncio
import logging
import random
from threading import Thread
from datetime import datetime
from flask import Flask
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from groq import Groq

# Мини-сервер
app = Flask('')
@app.route('/')
def home(): return "Балалай на кортах!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Настройки
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Список ID чатов, где бот будет активничать (заполнится автоматически при первом сообщении)
active_chats = set()

async def get_ai_response(user_text, user_name, is_random=False):
    try:
        if is_random:
            instruction = f"Ты — Балалай, дерзкий гопник на корточках. Твоя задача: внезапно и очень обидно подколоть {user_name} в чате. Используй черный юмор и дворовую эстетику. Не извиняйся."
            prompt = f"Выдай короткий и ядовитый подкол для {user_name}."
        else:
            instruction = f"Ты — Балалай, дерзкий и саркастичный гопник. Общаешься с {user_name}. Отвечай только по делу, используй черный юмор. НЕ упоминай Штурмослава без повода."
            prompt = user_text

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Слышь, че-то я приуныл... (Ошибка: {str(e)})"

# ФОНОВАЯ ЗАДАЧА: Подкол раз в 2 часа
async def random_roast_task():
    while True:
        await asyncio.sleep(7200) # Ровно 2 часа (7200 секунд)
        for chat_id in active_chats:
            try:
                # В этом режиме бот просто кидает случайную фразу в чат
                response_text = await get_ai_response("", "кого-нибудь", is_random=True)
                await bot.send_message(chat_id, response_text)
            except Exception:
                pass

# Обработка сообщений
@dp.message(F.text)
async def handle_message(message: Message):
    if message.from_user.is_bot: return
    
    active_chats.add(message.chat.id) # Запоминаем чат для рассылки
    
    bot_obj = await bot.get_me()
    bot_name = "балалай"
    
    # Условия ответа: упоминание имени или ответ на его сообщение
    is_mentioned = bot_name in message.text.lower()
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot_obj.id

    if is_mentioned or is_reply_to_bot:
        user_name = message.from_user.first_name
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        response_text = await get_ai_response(message.text, user_name)
        await message.reply(response_text)

async def main():
    Thread(target=run_web, daemon=True).start()
    asyncio.create_task(random_roast_task()) # Запускаем таймер подколов
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
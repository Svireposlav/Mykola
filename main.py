import os
import asyncio
import logging
import random
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from groq import Groq

# --- КОНФИГУРАЦИЯ ---
ALLOWED_CHAT_ID = -1002198634777
BOT_NAME_LOWER = "балалай"

app = Flask('')
@app.route('/')
def home(): return "Балалай на базе!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ЛОГИКА ИИ ---
async def get_ai_response(user_text, user_name, is_random=False):
    try:
        if is_random:
            instruction = (
                f"Ты — Балалай, дерзкий гопник с окраины. Твоя задача: внезапно и едко подколоть "
                f"кого-то из чата. Сейчас твоя цель — {user_name}. Используй жесткий черный юмор, "
                "цинизм и дворовой сленг. Будь краток и дерзок."
            )
            prompt = "Выдай один случайный ядовитый подкол."
        else:
            instruction = (
                f"Ты — Балалай, мастер сарказма и черного юмора. Общаешься с {user_name}. "
                "Отвечай дерзко, с издевкой, но по делу. НЕ упоминай Штурмослава, если не спросят. "
                "Веди себя как босс этого чата."
            )
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
        logging.error(f"Ошибка Groq: {e}")
        return "Че-то челюсть свело, не могу ответить..."

# --- ФОНОВЫЕ ПОДКОЛЫ ---
async def random_roast_task():
    while True:
        await asyncio.sleep(7200) # Раз в 2 часа
        try:
            # Пытаемся получить список участников или просто кидаем в чат общий подкол
            response_text = await get_ai_response("", "кого-то из вас", is_random=True)
            await bot.send_message(ALLOWED_CHAT_ID, response_text)
        except Exception as e:
            logging.error(f"Ошибка в таймере: {e}")

# --- ОБРАБОТКА СООБЩЕНИЙ ---
@dp.message(F.text)
async def handle_message(message: Message):
    # Жесткий фильтр по ID чата
    if message.chat.id != ALLOWED_CHAT_ID:
        return

    if message.from_user.is_bot:
        return

    bot_info = await bot.get_me()
    
    # Условия: обращение по имени или ответ на сообщение бота
    is_called = BOT_NAME_LOWER in message.text.lower()
    is_reply_to_me = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id

    if is_called or is_reply_to_me:
        user_name = message.from_user.first_name
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        response_text = await get_ai_response(message.text, user_name)
        await message.reply(response_text)

async def main():
    Thread(target=run_web, daemon=True).start()
    asyncio.create_task(random_roast_task())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
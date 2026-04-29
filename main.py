import os
import asyncio
import logging
import random
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from groq import Groq

# --- КОНФИГУРАЦИЯ ---
ALLOWED_CHAT_ID = -1002198634777
BOT_NAME_LOWER = "балалай"
MESSAGE_COUNTER = 0 # Счетчик для врыва каждые 30 сообщений
CHAT_HISTORY = [] # Память для анализа контекста

app = Flask('')
@app.route('/')
def home(): return "Балалай на кортах, Николаев на связи!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ЯДРО ЛИЧНОСТИ БАЛАЛАЯ ---
SYSTEM_PROMPT = (
    "Ты — Балалай, дерзкий гопник и смотрящий за чатом в Николаеве. "
    "Твой стиль: сочная тюремная феня, дворовой сленг Николаева (упоминай Намыв, Водопой, Корабельный, Слободку, Советскую). "
    "Ты мастер черного юмора и тюремных подколов. Общайся грубо, используй выражения типа: 'фраер', 'черт', 'балабол', 'вафля', 'шнырь', 'поясни за шмот', 'в натуре'. "
    "Избегай прямого мата, заменяй его на хлесткие тюремные эпитеты. Ты тут главный, остальные — массовка."
)

async def get_ai_response(prompt_text, user_name, mode="general"):
    try:
        context = "\n".join(CHAT_HISTORY[-15:]) # Берем последние 15 сообщений для контекста
        
        instructions = {
            "general": f"Ответь {user_name} на его сообщение. Будь дерзким.",
            "shmon": f"Проведи 'шмон' для {user_name}. Изучи контекст их общения: {context}. Выдай им жесткую характеристику по понятиям.",
            "fas": f"Выбери случайную жертву из чата и жестко 'опусти' его за его поведение. Используй тюремный жаргон.",
            "roast": "Ворвись в диалог внезапно. Выдай ядовитый комментарий по поводу последних сообщений в чате.",
            "timer": "Раз в 2 часа ты должен выйти из тени и докопаться до кого-то в чате просто так."
        }

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": f"Режим: {instructions.get(mode, 'general')}"},
                {"role": "user", "content": prompt_text}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        return "Че-то челюсть заклинило от вашего бреда..."

# --- ТАЙМЕР: РАЗ В 2 ЧАСА ---
async def random_roast_task():
    while True:
        await asyncio.sleep(7200) # 2 часа
        try:
            response_text = await get_ai_response("Выдай случайный подкол для чата.", "толпа", mode="timer")
            await bot.send_message(ALLOWED_CHAT_ID, response_text)
        except Exception as e:
            logging.error(f"Ошибка в таймере: {e}")

# --- КОМАНДЫ ---
@dp.message(Command("shmon"))
async def cmd_shmon(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    user_to_check = message.reply_to_message.from_user.first_name if message.reply_to_message else message.from_user.first_name
    await bot.send_chat_action(message.chat.id, "typing")
    res = await get_ai_response(f"Проведи шмон для {user_to_check}", user_to_check, mode="shmon")
    await message.answer(res)

@dp.message(Command("fas"))
async def cmd_fas(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    await bot.send_chat_action(message.chat.id, "typing")
    res = await get_ai_response("Атакуй случайного фраера", "случайный тип", mode="fas")
    await message.answer(res)

# --- ОСНОВНОЙ ОБРАБОТЧИК ---
@dp.message(F.text)
async def handle_message(message: Message):
    global MESSAGE_COUNTER, CHAT_HISTORY
    
    if message.chat.id != ALLOWED_CHAT_ID or message.from_user.is_bot:
        return

    # Запоминаем историю для анализа (держим последние 30 строк)
    CHAT_HISTORY.append(f"{message.from_user.first_name}: {message.text}")
    if len(CHAT_HISTORY) > 50: CHAT_HISTORY.pop(0)

    MESSAGE_COUNTER += 1
    
    bot_info = await bot.get_me()
    is_called = BOT_NAME_LOWER in message.text.lower()
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id

    # 1. Ответ на обращение
    if is_called or is_reply:
        await bot.send_chat_action(message.chat.id, "typing")
        res = await get_ai_response(message.text, message.from_user.first_name)
        await message.reply(res)

    # 2. Врыв каждые 30 сообщений
    elif MESSAGE_COUNTER >= 30:
        MESSAGE_COUNTER = 0
        await asyncio.sleep(2) # Небольшая пауза для естественности
        res = await get_ai_response("Ворвись в разговор и предъяви за базар", "чат", mode="roast")
        await bot.send_message(ALLOWED_CHAT_ID, res)

async def main():
    Thread(target=run_web, daemon=True).start()
    asyncio.create_task(random_roast_task())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
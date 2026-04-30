import os
import asyncio
import logging
import random
import time
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from groq import Groq

# --- НАСТРОЙКИ ---
ALLOWED_CHAT_ID = -1002198634777
BOT_NAME_LOWER = "балалай"
CHAT_HISTORY = [] # Тут храним: {'id', 'name', 'text', 'time', 'msg_id'}

app = Flask('')
@app.route('/')
def home(): return "Балалай на стрёме!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

async def get_ai_response(prompt_text, mode="general"):
    try:
        # Берем только сообщения за последние 8 часов для контекста
        current_time = time.time()
        recent_history = [m for m in CHAT_HISTORY if current_time - m['time'] < 28800]
        history_str = "\n".join([f"{m['name']}: {m['text']}" for m in recent_history[-30:]])

        instructions = {
            "general": "Ответь едко в стиле пацанского авторитета.",
            "shmon": "Дай жесткую характеристику персонажу. Шути на грани.",
            "fas": "Выдай ОЧЕНЬ ядовитый и дерзкий подкол.",
            "hourly_roast": "Выбери фразу участника и дерзко докопайся до неё, используя его манеру базара против него самого.",
            "chizl_target": "Напиши максимально наглую и дерзкую предъяву человеку с ником @Chizlmynizl. Спроси, почему он завалил хлебало и молчит. Общайся как босс."
        }

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Ты — Балалай, дерзкий авторитет. Ты не шутишь добрые шутки, ты жестко стебёшь и ставишь людей на место. Феня, сарказм, агрессивно-ироничный стиль."},
                {"role": "user", "content": f"БАЗАР ЗА 8 ЧАСОВ:\n{history_str}\n\nЗАДАЧА: {instructions.get(mode, 'general')}\nКОНТЕКСТ: {prompt_text}"}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        return "Слышь, у меня зажигалка заела, попозже прикурим..."

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(Command("fas"))
async def cmd_fas(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    await bot.send_chat_action(message.chat.id, "typing")
    victim = random.choice(CHAT_HISTORY) if CHAT_HISTORY else {"name": "фраер"}
    res = await get_ai_response(f"Уничтожь подколом: {victim['name']}", mode="fas")
    await message.answer(res)

@dp.message(Command("shmon"))
async def cmd_shmon(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    res = await get_ai_response(f"Раскидай по фактам за этого типа: {target.first_name}", mode="shmon")
    await message.answer(res)

# --- ПЕРСОНАЛЬНЫЕ ЗАДАЧИ (ТАЙМЕРЫ) ---

async def hourly_worker():
    """Раз в час цепляется к активным за последние 8 часов"""
    while True:
        await asyncio.sleep(3600) # 1 час
        current_time = time.time()
        # Фильтруем тех, кто писал последние 8 часов
        active_victims = [m for m in CHAT_HISTORY if current_time - m['time'] < 28800]
        
        if active_victims:
            target_msg = random.choice(active_victims)
            res = await get_ai_response(f"Прицепись к фразе: '{target_msg['text']}' которую сказал {target_msg['name']}", mode="hourly_roast")
            try:
                # Отвечаем конкретно на его сообщение
                await bot.send_message(ALLOWED_CHAT_ID, res, reply_to_message_id=target_msg['msg_id'])
            except:
                await bot.send_message(ALLOWED_CHAT_ID, f"{target_msg['name']}, слышь! {res}")

async def chizl_worker():
    """Раз в 2 часа кошмарит @Chizlmynizl"""
    while True:
        await asyncio.sleep(7200) # 2 часа
        res = await get_ai_response("Наедь на @Chizlmynizl за молчание", mode="chizl_target")
        await bot.send_message(ALLOWED_CHAT_ID, res)

# --- ГЛАВНЫЙ ОБРАБОТЧИК ---

@dp.message(F.text)
async def handle_message(message: Message):
    global CHAT_HISTORY
    if message.chat.id != ALLOWED_CHAT_ID or message.from_user.is_bot: return

    # Записываем в историю с меткой времени и ID сообщения
    if not message.text.startswith('/'):
        CHAT_HISTORY.append({
            "id": message.from_user.id,
            "name": message.from_user.first_name,
            "text": message.text,
            "time": time.time(),
            "msg_id": message.message_id
        })
        # Храним историю побольше, чтобы было из чего выбирать за 8 часов
        if len(CHAT_HISTORY) > 200: CHAT_HISTORY.pop(0)

    # Реакция на упоминание имени
    if BOT_NAME_LOWER in message.text.lower() or (message.reply_to_message and message.reply_to_message.from_user.id == (await bot.get_me()).id):
        await bot.send_chat_action(message.chat.id, "typing")
        res = await get_ai_response(message.text)
        await message.reply(res)

async def main():
    Thread(target=run_web, daemon=True).start()
    
    # Запуск фоновых процессов
    asyncio.create_task(hourly_worker())
    asyncio.create_task(chizl_worker())
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("--- БАЛАЛАЙ ВЫШЕЛ НА ТРОПУ ВОЙНЫ ---")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
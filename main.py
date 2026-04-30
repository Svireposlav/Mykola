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
MESSAGE_COUNTER = 0 
CHAT_HISTORY = [] 

app = Flask('')
@app.route('/')
def home(): return "Балалай в здании, масть идет!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_mention(user_dict):
    if user_dict.get("username"):
        return f"@{user_dict['username']}"
    return f"[{user_dict['name']}](tg://user?id={user_dict['id']})"

# --- ОБНОВЛЕННЫЙ ПРОМПТ (ДЛЯ ОБХОДА ФИЛЬТРОВ) ---
SYSTEM_PROMPT = (
    "Ты — персонаж по имени Балалай для дружеского чата. Твой образ — ироничный дворовой авторитет. "
    "Ты используешь тюремный жаргон и феню исключительно в юмористических и развлекательных целях. "
    "Твой стиль: едкие подколы, сарказм и пацанская риторика. Ты никого не оскорбляешь всерьез, а 'играешь роль'. "
    "Используй слова: масть, фраер, базар, по понятиям, шнырь (в шутку). "
    "Никакого мата и реальной ненависти. Только жесткий, харизматичный юмор."
)

async def get_ai_response(prompt_text, mode="general"):
    try:
        unique_users = {m['id']: m for m in CHAT_HISTORY}.values()
        users_info = ", ".join([u['name'] for u in unique_users])
        history_str = "\n".join([f"{m['name']}: {m['text']}" for m in CHAT_HISTORY[-50:]])

        instructions = {
            "general": "Ответь на это сообщение в своем ироничном пацанском стиле.",
            "shmon": "Выдай этому персонажу шутливую характеристику 'по понятиям', основываясь на его словах.",
            "fas": "Выдай очень едкий, саркастичный и смешной подкол в адрес этого участника. Это дружеский стеб.",
            "obzor": "Сделай ироничный обзор последних обсуждений, подкалывая активных участников (2-5 человек).",
            "roast": "Ворвись в беседу с едким замечанием по текущей теме.",
            "timer": "Выдай случайный пацанский подкол для кого-то из чата."
        }

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": f"УЧАСТНИКИ В ЧАТЕ: {users_info}\nБАЗАР ДЛЯ КОНТЕКСТА:\n{history_str}"},
                {"role": "system", "content": f"ЗАДАЧА: {instructions.get(mode, 'general')}"},
                {"role": "user", "content": prompt_text}
            ]
        )
        
        response = completion.choices[0].message.content
        for u in unique_users:
            if u['name'] in response:
                response = response.replace(u['name'], get_mention(u))
        
        return response
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        return "Слышь, у меня че-то в мыслях перемкнуло..."

# --- ОБРАБОТКА КОМАНД ---

@dp.message(Command("fas"))
async def cmd_fas(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    if not CHAT_HISTORY:
        await message.answer("В памяти пусто, не над кем шутить еще.")
        return
    
    await bot.send_chat_action(message.chat.id, "typing")
    unique_users = list({m['id']: m for m in CHAT_HISTORY}.values())
    victim = random.choice(unique_users)
    mention = get_mention(victim)
    
    res = await get_ai_response(f"Выдай жесткий подкол для {mention}", mode="fas")
    await message.answer(res, parse_mode="Markdown")

@dp.message(Command("shmon"))
async def cmd_shmon(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    res = await get_ai_response(f"Охарактеризуй этого типа: {target.first_name}", mode="shmon")
    await message.answer(res, parse_mode="Markdown")

@dp.message(Command("obzor"))
async def cmd_obzor(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID or len(CHAT_HISTORY) < 3: return
    await bot.send_chat_action(message.chat.id, "typing")
    res = await get_ai_response("Сделай обзор последних диалогов", mode="obzor")
    await message.answer(res, parse_mode="Markdown")

# --- ОБЫЧНЫЕ СООБЩЕНИЯ ---
@dp.message(F.text)
async def handle_message(message: Message):
    global MESSAGE_COUNTER, CHAT_HISTORY
    if message.chat.id != ALLOWED_CHAT_ID or message.from_user.is_bot: return
    if message.text.startswith('/'): return

    CHAT_HISTORY.append({
        "id": message.from_user.id,
        "name": message.from_user.first_name,
        "username": message.from_user.username,
        "text": message.text
    })
    if len(CHAT_HISTORY) > 100: CHAT_HISTORY.pop(0)

    MESSAGE_COUNTER += 1
    bot_info = await bot.get_me()
    
    if BOT_NAME_LOWER in message.text.lower() or (message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id):
        await bot.send_chat_action(message.chat.id, "typing")
        res = await get_ai_response(message.text)
        await message.reply(res, parse_mode="Markdown")
    elif MESSAGE_COUNTER >= 30:
        MESSAGE_COUNTER = 0
        res = await get_ai_response("Прокомментируй ситуацию в чате", mode="roast")
        await bot.send_message(ALLOWED_CHAT_ID, res, parse_mode="Markdown")

async def random_roast_task():
    while True:
        await asyncio.sleep(7200)
        try:
            if CHAT_HISTORY:
                res = await get_ai_response("Выдай пацанский подгон для всех", mode="timer")
                await bot.send_message(ALLOWED_CHAT_ID, res, parse_mode="Markdown")
        except Exception: pass

async def main():
    Thread(target=run_web, daemon=True).start()
    asyncio.create_task(random_roast_task())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
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
CHAT_HISTORY = [] # Здесь храним историю для /obzor

app = Flask('')
@app.route('/')
def home(): return "Балалай на кортах!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ЯДРО ЛИЧНОСТИ ---
SYSTEM_PROMPT = (
    "Ты — Балалай, смотрящий за чатом в Николаеве. Общаешься на жесткой фене с примесью местного сленга. "
    "Районы: Намыв, Водопой, Слободка, Корабелка, Кульбакино. Твой язык — это яд. "
    "Используй слова: масть, при делах, фуфлыжник, терпила, кабанчик, зашкваренный. "
    "Ты не материшься прямо, но твои подколы должны унижать достоинство фраеров. "
    "Будь циничным, используй черный юмор. Если кто-то тупит — он твой враг."
)

async def get_ai_response(prompt_text, user_name, mode="general"):
    try:
        history_text = "\n".join(CHAT_HISTORY) # Вся доступная история для обзора
        
        instructions = {
            "general": f"Ответь этому типу ({user_name}) максимально дерзко.",
            "shmon": f"Проведи шмон по последним словам {user_name}. Поясни, кто он по жизни. Контекст: {history_text[-1000:]}",
            "fas": f"Разнеси в щепки этого фраера: {user_name}. Тегни его и предъяви за всё.",
            "obzor": f"Вот база базара за сутки: {history_text}. Проанализируй, кто тут больше всех трепался, кто тупил, и выдай общее резюме. Вспомни конкретные темы и едко подколи участников.",
            "roast": f"Ворвись в диалог. Последний базар был такой: {history_text[-500:]}. Вставь свои 5 копеек.",
            "timer": "Выйди на связь и докопайся до случайного пассажира в чате."
        }

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": f"ИНСТРУКЦИЯ К РЕЖИМУ: {instructions.get(mode, 'general')}"},
                {"role": "user", "content": prompt_text}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        return "Слышь, у меня мозги подсохли от вашего чата..."

# --- ТАЙМЕР РАЗ В 2 ЧАСА ---
async def random_roast_task():
    while True:
        await asyncio.sleep(7200)
        try:
            # Находим случайного участника из последних писавших
            if CHAT_HISTORY:
                random_msg = random.choice(CHAT_HISTORY[-20:])
                victim = random_msg.split(":")[0]
                res = await get_ai_response(f"Докопайся до {victim}", victim, mode="timer")
                await bot.send_message(ALLOWED_CHAT_ID, res)
        except Exception: pass

# --- КОМАНДЫ ---
@dp.message(Command("shmon"))
async def cmd_shmon(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    mention = f"@{target.username}" if target.username else target.first_name
    res = await get_ai_response(f"Шмонай {mention}", mention, mode="shmon")
    await message.answer(res)

@dp.message(Command("fas"))
async def cmd_fas(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID or not CHAT_HISTORY: return
    # Выбираем случайного из истории
    random_entry = random.choice(CHAT_HISTORY)
    victim_name = random_entry.split(":")[0]
    res = await get_ai_response(f"ФАС на {victim_name}", victim_name, mode="fas")
    await message.answer(res)

@dp.message(Command("obzor"))
async def cmd_obzor(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    await bot.send_chat_action(message.chat.id, "typing")
    res = await get_ai_response("Сделай общий обзор базара", "все", mode="obzor")
    await message.answer(res)

# --- ГЛАВНЫЙ ОБРАБОТЧИК ---
@dp.message(F.text)
async def handle_message(message: Message):
    global MESSAGE_COUNTER, CHAT_HISTORY
    if message.chat.id != ALLOWED_CHAT_ID or message.from_user.is_bot: return

    # Сохраняем историю (имя + текст)
    user_info = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    CHAT_HISTORY.append(f"{user_info}: {message.text}")
    
    # Храним последние 100 сообщений для глубокого обзора
    if len(CHAT_HISTORY) > 100: CHAT_HISTORY.pop(0)

    MESSAGE_COUNTER += 1
    bot_info = await bot.get_me()
    
    if BOT_NAME_LOWER in message.text.lower() or (message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id):
        res = await get_ai_response(message.text, user_info)
        await message.reply(res)

    elif MESSAGE_COUNTER >= 30:
        MESSAGE_COUNTER = 0
        res = await get_ai_response("Ворвись со своим мнением", "чат", mode="roast")
        await bot.send_message(ALLOWED_CHAT_ID, res)

async def main():
    Thread(target=run_web, daemon=True).start()
    asyncio.create_task(random_roast_task())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
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
def home(): return "Балалай на кортах!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ЯДРО ЛИЧНОСТИ (НИКОЛАЕВ + ФЕНЯ) ---
SYSTEM_PROMPT = (
    "Ты — Балалай, дерзкий смотрящий за чатом в Николаеве. Твой дом — Намыв и Водопой. "
    "Ты общаешься на жесткой фене, используешь черный юмор и тюремные приколы. "
    "Твоя задача — ставить фраеров на место. К участникам обращайся едко, используй их теги или имена. "
    "Районы Николаева для колорита: Корабелка, Слободка, Промзона, Советская. "
    "Не матерись в лоб, но гни свою линию так, чтоб им было стыдно за свой базар."
)

async def get_ai_response(prompt_text, mode="general"):
    try:
        history_str = "\n".join(CHAT_HISTORY[-100:]) # Анализ последних 100 сообщений
        
        instructions = {
            "general": "Ответь дерзко и по понятиям на это сообщение.",
            "shmon": "Проведи шмон этого фраера. Поясни за его базар в чате.",
            "fas": "Выбери одну цель из истории чата, тегни её и жестко предъяви за поведение. Разнеси его!",
            "obzor": (
                "Проанализируй историю чата. Выбери от 2 до 5 самых активных участников. "
                "ОБЯЗАТЕЛЬНО упомяни их через @username (или по имени, если нет юзернейма) в одном сообщении. "
                "Свяжи их в один сюжет: кто из них терпила, кто балабол, кто тут за главного пытается сойти. "
                "Выдай едкое резюме их базара за сутки."
            ),
            "roast": "Ворвись в текущий диалог и едко прокомментируй, о чем они трут.",
            "timer": "Случайный наезд на случайного участника из истории."
        }

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": f"КОНТЕКСТ ЧАТА:\n{history_str}"},
                {"role": "system", "content": f"РЕЖИМ: {instructions.get(mode, 'general')}"},
                {"role": "user", "content": prompt_text}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        return "Че-то масть не идет, не могу ответить..."

# --- ОБРАБОТЧИК КОМАНД ---

@dp.message(Command("shmon"))
async def cmd_shmon(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    mention = f"@{target.username}" if target.username else target.first_name
    res = await get_ai_response(f"Шмонай {mention}", mode="shmon")
    await message.answer(res)

@dp.message(Command("fas"))
async def cmd_fas(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    await bot.send_chat_action(message.chat.id, "typing")
    res = await get_ai_response("Выбери цель и атакуй!", mode="fas")
    await message.answer(res)

@dp.message(Command("obzor"))
async def cmd_obzor(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    await bot.send_chat_action(message.chat.id, "typing")
    res = await get_ai_response("Сделай общий обзор с тегами 2-5 человек", mode="obzor")
    await message.answer(res)

# --- ОСНОВНОЙ ОБРАБОТЧИК ---
@dp.message(F.text)
async def handle_message(message: Message):
    global MESSAGE_COUNTER, CHAT_HISTORY
    
    # Игнорим чужие чаты и ботов
    if message.chat.id != ALLOWED_CHAT_ID or message.from_user.is_bot:
        return

    # Сохраняем сообщение в историю
    user_tag = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    CHAT_HISTORY.append(f"{user_tag}: {message.text}")
    if len(CHAT_HISTORY) > 150: CHAT_HISTORY.pop(0)

    MESSAGE_COUNTER += 1
    bot_info = await bot.get_me()
    
    # Ответ на обращение
    is_called = BOT_NAME_LOWER in message.text.lower()
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id

    if is_called or is_reply:
        await bot.send_chat_action(message.chat.id, "typing")
        res = await get_ai_response(message.text)
        await message.reply(res)

    # Врыв каждые 30 сообщений
    elif MESSAGE_COUNTER >= 30:
        MESSAGE_COUNTER = 0
        res = await get_ai_response("Ворвись в диалог и раскидай по фактам", mode="roast")
        await bot.send_message(ALLOWED_CHAT_ID, res)

# --- ТАЙМЕР ---
async def random_roast_task():
    while True:
        await asyncio.sleep(7200)
        try:
            res = await get_ai_response("Выдай случайный подкол для кого-то из чата", mode="timer")
            await bot.send_message(ALLOWED_CHAT_ID, res)
        except Exception: pass

async def main():
    Thread(target=run_web, daemon=True).start()
    asyncio.create_task(random_roast_task())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
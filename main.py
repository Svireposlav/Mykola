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
def home(): return "Балалай на базе, Николаев в курсе!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ТЕГОВ ---
def get_mention(user_dict):
    if user_dict.get("username"):
        return f"@{user_dict['username']}"
    return f"[{user_dict['name']}](tg://user?id={user_dict['id']})"

# --- ЯДРО ЛИЧНОСТИ ---
SYSTEM_PROMPT = (
    "Ты — Балалай, дерзкий и авторитетный тип из Николаева. Твой стиль — сочная тюремная феня и черный юмор. "
    "Ты общаешься жестко, цинично, ставя фраеров на место. "
    "ВАЖНО: Упоминай районы Николаева (Намыв, Слободка, Корабелка и др.) ОЧЕНЬ РЕДКО, только если это реально в тему. Не спамь ими. "
    "Используй только имена/теги реальных людей из предоставленного списка. Не выдумывай персонажей. "
    "Ты не материшься прямо, но унижаешь словом так, что оппоненту хочется выйти из чата."
)

async def get_ai_response(prompt_text, mode="general"):
    try:
        # Собираем уникальных участников
        unique_users = {m['id']: m for m in CHAT_HISTORY}.values()
        users_info = "\n".join([f"- {u['name']} (ID: {u['id']}, @{u['username'] or 'нет'})" for u in unique_users])
        history_str = "\n".join([f"{m['name']}: {m['text']}" for m in CHAT_HISTORY[-100:]])

        instructions = {
            "general": "Ответь этому типу максимально едко, используя контекст.",
            "shmon": "Поясни за этого персонажа, основываясь на его базаре. Кто он по масти?",
            "fas": "Выбери одного из списка участников, тегни его и устрой ему лютый разнос.",
            "obzor": (
                "Проанализируй базар. Выбери от 2 до 5 самых активных. "
                "ОБЯЗАТЕЛЬНО упомяни их имена в тексте. Выдай ядовитое резюме их общения. "
                "Районы Николаева упоминай только если это крайне уместно, не чаще одного раза за весь текст."
            ),
            "roast": "Ворвись в диалог и раскидай всех по фактам. Используй реальные имена.",
            "timer": "Случайный наезд на кого-то из списка участников."
        }

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": f"РЕАЛЬНЫЕ УЧАСТНИКИ:\n{users_info}"},
                {"role": "system", "content": f"ПОСЛЕДНИЕ СООБЩЕНИЯ:\n{history_str}"},
                {"role": "system", "content": f"РЕЖИМ: {instructions.get(mode, 'general')}"},
                {"role": "user", "content": prompt_text}
            ]
        )
        
        response = completion.choices[0].message.content
        
        # Автоматическая замена имен на кликабельные теги/ссылки
        for u in unique_users:
            if u['name'] in response:
                mention = get_mention(u)
                response = response.replace(u['name'], mention)
        
        return response
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        return "Че-то челюсть свело, не могу ответить..."

# --- ОБРАБОТЧИК КОМАНД ---

@dp.message(Command("shmon"))
async def cmd_shmon(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    res = await get_ai_response(f"Проведи шмон для {target.first_name}", mode="shmon")
    await message.answer(res, parse_mode="Markdown")

@dp.message(Command("fas"))
async def cmd_fas(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID or not CHAT_HISTORY: return
    await bot.send_chat_action(message.chat.id, "typing")
    res = await get_ai_response("Выбери цель из списка и атакуй!", mode="fas")
    await message.answer(res, parse_mode="Markdown")

@dp.message(Command("obzor"))
async def cmd_obzor(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID or len(CHAT_HISTORY)
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
CHAT_HISTORY = [] # Память: [{"id": 1, "name": "A", "username": "b", "text": "..."}]

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

# --- ФУНКЦИЯ ДЛЯ СОЗДАНИЯ ТЕГА (УПОМИНАНИЯ) ---
def get_mention(user_dict):
    if user_dict.get("username"):
        return f"@{user_dict['username']}"
    # Если юзернейма нет, делаем текстовую ссылку по ID
    return f"[{user_dict['name']}](tg://user?id={user_dict['id']})"

# --- ЯДРО ЛИЧНОСТИ БАЛАЛАЯ ---
SYSTEM_PROMPT = (
    "Ты — Балалай, дерзкий и авторитетный смотрящий за чатом. Твой стиль — жесткая тюремная феня, "
    "цинизм и острый черный юмор. Ты общаешься свысока, ставя фраеров на место. "
    "Твоя задача — хлестко подкалывать РЕАЛЬНЫХ участников чата. "
    "Используй только предоставленные имена и юзернеймы. Не выдумывай людей. "
    "Никаких упоминаний городов или районов. Ты не материшься прямо, но унижаешь словом."
)

async def get_ai_response(prompt_text, mode="general"):
    try:
        # Формируем список живых душ для ИИ
        unique_users = {m['id']: m for m in CHAT_HISTORY}.values()
        users_info = "\n".join([f"- {u['name']} (@{u['username'] or 'нет юзернейма'})" for u in unique_users])
        history_str = "\n".join([f"{m['name']}: {m['text']}" for m in CHAT_HISTORY[-100:]])

        instructions = {
            "general": "Ответь этому фраеру максимально едко по контексту последнего сообщения.",
            "shmon": "Поясни за этого персонажа. Кто он по масти, судя по его словам?",
            "fas": "Перед тобой цель. Устрой ей лютый разнос, предъяви за всё по понятиям. Будь беспощаден.",
            "obzor": (
                "Проанализируй базар. Выбери от 2 до 5 самых активных участников. "
                "ОБЯЗАТЕЛЬНО упомяни их имена/теги в тексте. Выдай ядовитый итог их общения."
            ),
            "roast": "Ворвись в диалог и раскидай всех. Используй реальные имена из истории.",
            "timer": "Случайный наезд на кого-то из присутствующих в списке участников."
        }

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": f"УЧАСТНИКИ В ЧАТЕ:\n{users_info}"},
                {"role": "system", "content": f"ИСТОРИЯ БАЗАРА:\n{history_str}"},
                {"role": "system", "content": f"РЕЖИМ: {instructions.get(mode, 'general')}"},
                {"role": "user", "content": prompt_text}
            ]
        )
        
        response = completion.choices[0].message.content
        
        # Заменяем имена в ответе на кликабельные ссылки/теги
        for u in unique_users:
            if u['name'] in response:
                mention = get_mention(u)
                response = response.replace(u['name'], mention)
        
        return response
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        return "Че-то челюсть свело, не могу ответить..."

# --- КОМАНДЫ ---

@dp.message(Command("shmon"))
async def cmd_shmon(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    res = await get_ai_response(f"Шмонай этого: {target.first_name}", mode="shmon")
    await message.answer(res, parse_mode="Markdown")

@dp.message(Command("fas"))
async def cmd_fas(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    if not CHAT_HISTORY:
        await message.answer("В памяти пусто, фраера еще не наследили. Попиздите, чтоб я вас запомнил!")
        return
    
    await bot.send_chat_action(message.chat.id, "typing")
    # Принудительный выбор жертвы прямо здесь
    unique_users = list({m['id']: m for m in CHAT_HISTORY}.values())
    victim = random.choice(unique_users)
    mention = get_mention(victim)
    
    res = await get_ai_response(f"ФАС на {mention}!", mode="fas")
    await message.answer(res, parse_mode="Markdown")

@dp.message(Command("obzor"))
async def cmd_obzor(message: Message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    if len(CHAT_HISTORY) < 3:
        await message.answer("Мало базара для обзора. Накидайте сообщений сначала.")
        return
    await bot.send_chat_action(message.chat.id, "typing")
    res = await get_ai_response("Сделай обзор с тегами 2-5 активных участников", mode="obzor")
    await message.answer(res, parse_mode="Markdown")

# --- ГЛАВНЫЙ ОБРАБОТЧИК СООБЩЕНИЙ ---
@dp.message(F.text)
async def handle_message(message: Message):
    global MESSAGE_COUNTER, CHAT_HISTORY
    if message.chat.id != ALLOWED_CHAT_ID or message.from_user.is_bot: return

    # Сохраняем участника в историю
    CHAT_HISTORY.append({
        "id": message.from_user.id,
        "name": message.from_user.first_name,
        "username": message.from_user.username,
        "text": message.text
    })
    if len(CHAT_HISTORY) > 200: CHAT_HISTORY.pop(0)

    MESSAGE_COUNTER += 1
    bot_info = await bot.get_me()
    
    is_called = BOT_NAME_LOWER in message.text.lower()
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id

    if is_called or is_reply:
        await bot.send_chat_action(message.chat.id, "typing")
        res = await get_ai_response(message.text)
        await message.reply(res, parse_mode="Markdown")

    elif MESSAGE_COUNTER >= 30:
        MESSAGE_COUNTER = 0
        res = await get_ai_response("Ворвись в базар и раскидай по фактам", mode="roast")
        await bot.send_message(ALLOWED_CHAT_ID, res, parse_mode="Markdown")

# --- ЦИКЛИЧЕСКИЙ ТАЙМЕР (РАЗ В 2 ЧАСА) ---
async def random_roast_task():
    while True:
        await asyncio.sleep(7200)
        try:
            if CHAT_HISTORY:
                res = await get_ai_response("Случайный наезд на кого-то", mode="timer")
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
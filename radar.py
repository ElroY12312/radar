import re
import os
import logging
import asyncio
import aiohttp
from flask import Flask
from telethon import TelegramClient, events

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Получаем переменные окружения
api_id = int(os.getenv("API_ID", "0"))
api_hash = os.getenv("API_HASH", "")
source_channel_id = int(os.getenv("SOURCE_CHANNEL_ID", "0"))
destination_channel_id = int(os.getenv("DESTINATION_CHANNEL_ID", "0"))
session_name = os.getenv("SESSION_NAME", "session")

# Проверка обязательных переменных окружения
if not api_id or not api_hash or not source_channel_id or not destination_channel_id:
    raise ValueError("❌ ОШИБКА: Одна или несколько переменных окружения не заданы!")

client = TelegramClient(session_name, api_id, api_hash)

# Словарь для фильтрации
blacklist_words = {"донат", "підтримати", "реклама", "підписка", "переказ на карту", "пожертва", "допомога", "підтримка", "збір", "задонатити"}

# Регулярные выражения
card_pattern = re.compile(r'\b(?:\d[ -]*){12,19}\b|\bUA\d{25,}\b')
url_pattern = re.compile(r'https?://\S+', re.IGNORECASE)
city_pattern = re.compile(r'Стежити за обстановкою .*? можна тут - \S+', re.IGNORECASE)
random_letters_pattern = re.compile(r'^\s*[а-яА-Яa-zA-Z]{4,}\s*$', re.MULTILINE)
unwanted_text_pattern = re.compile(r'(Підтримати канал, буду вдячний Вам:|🔗Посилання на банку)', re.IGNORECASE)

extra_text = '🇺🇦 <a href="https://t.me/+9RxqorgcHYZkYTQy">Небесний Вартовий</a>'

# Убираем Flask, так как он не используется для основной работы бота
async def run_web():
    port = int(os.getenv("PORT", 10000))
    from aiohttp import web
    async def home(request):
        return web.Response(text="Бот работает!")
    app = web.Application()
    app.router.add_get('/', home)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def fake_requests():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get("https://твой-сервис.onrender.com/") as response:
                    logger.info("Фейковый запрос отправлен на Render.")
            except Exception as e:
                logger.warning(f"Ошибка при отправке фейкового запроса: {e}")
            
            await asyncio.sleep(120)

@app.route('/start')
async def start(request):
    return "Bot is running!"

# Асинхронная обработка сообщений
@client.on(events.NewMessage(chats=source_channel_id))
async def handler(event):
    try:
        message_text = event.message.raw_text or ""
        message_media = event.message.media

        # Фильтрация текста
        message_text = re.sub(url_pattern, '', message_text)
        message_text = re.sub(city_pattern, '', message_text).strip()
        message_text = re.sub(random_letters_pattern, '', message_text).strip()
        message_text = re.sub(unwanted_text_pattern, '', message_text).strip()

        if any(word in message_text for word in blacklist_words) or card_pattern.search(message_text):
            logger.info("Сообщение заблокировано из-за фильтрации.")
            return

        # Отправка медиа
        if not message_text and message_media:
            await client.send_file(destination_channel_id, message_media)
            logger.info("Отправлено только фото.")
            return

        if message_text:
            message_text += f"\n\n{extra_text}"

        # Отправка сообщения с медиа или без
        if message_media:
            await client.send_file(destination_channel_id, message_media, caption=message_text, parse_mode='html')
            logger.info("Отправлено фото с текстом.")
        else:
            await client.send_message(destination_channel_id, message_text, link_preview=False, parse_mode='html')
            logger.info("Отправлено текстовое сообщение.")

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")

# Основной цикл бота
async def main():
    try:
        await client.start()
        logger.info("Бот запущен и ожидает сообщения...")
        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Ошибка при подключении к Telegram API: {e}. Перезапуск через 10 секунд...")
        await asyncio.sleep(10)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    # Запуск веб-сервера и фейковых запросов в фоне
    loop.create_task(run_web())
    loop.create_task(fake_requests())

    # Запуск бота
    loop.run_until_complete(main())

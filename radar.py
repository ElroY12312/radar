import re
import os
import logging
import asyncio
import threading
import requests
from flask import Flask
from telethon import TelegramClient, events
import time

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

api_id = int(os.getenv("API_ID", "17082218"))  # Используем переменные окружения для Replit
api_hash = os.getenv("API_HASH", "6015a38682c3f6265ac55a1e35b1240a")
source_channel_id = int(os.getenv("SOURCE_CHANNEL_ID", "-1002279229082"))
destination_channel_id = int(os.getenv("DESTINATION_CHANNEL_ID", "-1002264693466"))
session_path = os.path.join(os.getcwd(), "session_name.session")  # Используем путь для Replit
uptime_url = os.getenv("UPTIME_URL", "")  # URL для UptimeRobot

if not api_id or not api_hash or not source_channel_id or not destination_channel_id:
    raise ValueError("❌ ОШИБКА: Одна или несколько переменных окружения не заданы!")

client = TelegramClient(session_path, api_id, api_hash)

blacklist_words = {"донат", "підтримати", "реклама", "підписка", "переказ на карту", "пожертва", "допомога", "підтримка", "збір", "задонатити"}

card_pattern = re.compile(r'\b(?:\d[ -]*){12,19}\b|\bUA\d{25,}\b')
url_pattern = re.compile(r'https?://\S+', re.IGNORECASE)
city_pattern = re.compile(r'Стежити за обстановкою .*? можна тут - \S+', re.IGNORECASE)
random_letters_pattern = re.compile(r'^\s*[а-яА-Яa-zA-Z]{4,}\s*$', re.MULTILINE)
unwanted_text_pattern = re.compile(r'(Підтримати канал, буду вдячний Вам:|🔗Посилання на банку)', re.IGNORECASE)

extra_text = '🇺🇦 <a href="https://t.me/+9RxqorgcHYZkYTQy">Небесний Вартовий</a>'

@app.route('/')
def home():
    return "Бот работает!"

def run_web():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def uptime_ping():
    while True:
        if uptime_url:
            try:
                requests.get(uptime_url)
                logger.info("✅ Отправлен пинг для UptimeRobot.")
            except Exception as e:
                logger.warning(f"⚠ Ошибка при отправке пинга: {e}")
        time.sleep(300)  # Каждые 5 минут

threading.Thread(target=run_web, daemon=True).start()
threading.Thread(target=uptime_ping, daemon=True).start()

@client.on(events.NewMessage(chats=source_channel_id))
async def handler(event):
    try:
        message_text = event.message.raw_text or ""
        message_media = event.message.media

        message_text = re.sub(url_pattern, '', message_text)
        message_text = re.sub(city_pattern, '', message_text).strip()
        message_text = re.sub(random_letters_pattern, '', message_text).strip()
        message_text = re.sub(unwanted_text_pattern, '', message_text).strip()

        if any(word in message_text for word in blacklist_words) or card_pattern.search(message_text):
            logger.info("Сообщение заблокировано из-за фильтрации.")
            return

        if not message_text and message_media:
            await client.send_file(destination_channel_id, message_media)
            logger.info("Отправлено только фото.")
            return

        if message_text:
            message_text += f"\n\n{extra_text}"

        if message_media:
            await client.send_file(destination_channel_id, message_media, caption=message_text, parse_mode='html')
            logger.info("Отправлено фото с текстом.")
        else:
            await client.send_message(destination_channel_id, message_text, link_preview=False, parse_mode='html')
            logger.info("Отправлено текстовое сообщение.")

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")

async def main():
    while True:
        try:
            await client.start()
            logger.info("Бот запущен и ожидает сообщения...")
            await client.run_until_disconnected()
        except Exception as e:
            logger.error(f"Ошибка: {e}. Перезапуск через 5 секунд...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

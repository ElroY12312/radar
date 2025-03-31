import re
import os
import logging
import asyncio
import threading
import requests
from flask import Flask
from telethon import TelegramClient, events

# Настройка Flask-приложения
app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
api_id = int(os.getenv("API_ID", "0"))
api_hash = os.getenv("API_HASH", "")
source_channel_id = int(os.getenv("SOURCE_CHANNEL_ID", "0"))
destination_channel_id = int(os.getenv("DESTINATION_CHANNEL_ID", "0"))
session_name = os.getenv("SESSION_NAME", "session")

# URL для UptimeRobot
server_url = os.getenv("SERVER_URL", "http://localhost:10000")

# Проверка корректности переменных окружения
if not api_id or not api_hash or not source_channel_id or not destination_channel_id:
    raise ValueError("❌ ОШИБКА: Одна или несколько переменных окружения не заданы!")

logger.info(f"API_ID: {api_id}, API_HASH: {api_hash}, SOURCE_CHANNEL_ID: {source_channel_id}, DESTINATION_CHANNEL_ID: {destination_channel_id}")

# Инициализация Telegram-клиента
client = TelegramClient(session_name, api_id, api_hash)

# Регулярные выражения для фильтрации сообщений
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

# Функция для регулярного пинга сервера
def ping_server():
    while True:
        try:
            requests.get(server_url)
            logger.info("Пинг отправлен на сервер (UptimeRobot).")
        except Exception as e:
            logger.error(f"Ошибка при пинге: {e}")
        asyncio.run(asyncio.sleep(1500))  # 25 минут (UptimeRobot пингует раз в 5 минут)

# Запуск Flask и пингера в отдельных потоках
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=10000), daemon=True).start()
threading.Thread(target=ping_server, daemon=True).start()

# Обработчик новых сообщений из источника
@client.on(events.NewMessage(chats=source_channel_id))
async def handler(event):
    try:
        message_text = event.message.raw_text or ""
        message_media = event.message.media

        # Фильтрация текста сообщений
        message_text = re.sub(url_pattern, '', message_text)
        message_text = re.sub(city_pattern, '', message_text).strip()
        message_text = re.sub(random_letters_pattern, '', message_text).strip()
        message_text = re.sub(unwanted_text_pattern, '', message_text).strip()

        # Проверка на черный список
        if any(word in message_text for word in blacklist_words) or card_pattern.search(message_text):
            logger.info("Сообщение заблокировано из-за фильтрации.")
            return

        # Отправка медиа
        if not message_text and message_media:
            await client.send_file(destination_channel_id, message_media)
            logger.info("Отправлено только фото.")
            return

        # Отправка текста с медиа
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

# Основная асинхронная функция для запуска Telegram клиента
async def main():
    while True:
        try:
            await client.start()
            logger.info("Бот запущен и ожидает сообщения...")
            await client.run_until_disconnected()
        except Exception as e:
            logger.error(f"Ошибка: {e}. Перезапуск через 5 секунд...")
            await asyncio.sleep(5)

# Запуск асинхронной функции
if __name__ == "__main__":
    asyncio.run(main())

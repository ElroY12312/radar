import re
import os
import logging
import asyncio
from telethon import TelegramClient, events

# Настроим логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
api_id = int(os.getenv("API_ID", "0"))
api_hash = os.getenv("API_HASH", "")
source_channel_id = int(os.getenv("SOURCE_CHANNEL_ID", "0"))
destination_channel_id = int(os.getenv("DESTINATION_CHANNEL_ID", "0"))

if not api_id or not api_hash or not source_channel_id or not destination_channel_id:
    raise ValueError("Одна или несколько переменных окружения не заданы!")

client = TelegramClient('session_name', api_id, api_hash)

# Фильтры
blacklist_words = {"донат", "підтримати", "реклама", "підписка", "переказ на карту",
                   "пожертва", "допомога", "підтримка", "збір", "задонатити"}

card_pattern = re.compile(r'\b(?:\d[ -]*){12,19}\b|\bUA\d{25,}\b')
url_pattern = re.compile(r'https?://\S+', re.IGNORECASE)
city_pattern = re.compile(r'Стежити за обстановкою .*? можна тут - \S+', re.IGNORECASE)
random_letters_pattern = re.compile(r'^\s*[а-яА-Яa-zA-Z]{4,}\s*$', re.MULTILINE)

# Добавляемый текст
extra_text = '🇺🇦 <a href="https://t.me/+9RxqorgcHYZkYTQy">Небесний Вартовий</a>'

@client.on(events.NewMessage(chats=source_channel_id))
async def handler(event):
    try:
        message_text = event.message.raw_text or ""
        message_media = event.message.media

        # Очистка текста
        message_text = re.sub(url_pattern, '', message_text)
        message_text = re.sub(city_pattern, '', message_text).strip()
        message_text = re.sub(random_letters_pattern, '', message_text).strip()

        # Фильтрация запрещенного контента
        if any(word in message_text for word in blacklist_words) or card_pattern.search(message_text):
            logger.info("Сообщение заблокировано из-за фильтрации.")
            return

        # Отправка сообщений
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
    await client.start()
    logger.info("Бот запущен и ожидает сообщения...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

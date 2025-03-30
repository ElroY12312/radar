import re
from telethon import TelegramClient, events
import os

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
source_channel_id = int(os.getenv("SOURCE_CHANNEL_ID"))
destination_channel_id = int(os.getenv("DESTINATION_CHANNEL_ID"))


client = TelegramClient('session_name', api_id, api_hash)

# Ключевые слова для фильтрации рекламы, сборов и помощи
blacklist_words = [
    "донат", "підтримати", "реклама", "підписка", "переказ на карту",
    "пожертва", "допомога", "підтримка", "збір", "задонатити"
]

# Регулярное выражение для поиска номеров карт (Visa, Mastercard, IBAN)
card_pattern = re.compile(r'\b(?:\d[ -]*){12,19}\b|\bUA\d{25,}\b')

# Регулярное выражение для удаления ссылок, встроенных в слова
url_pattern = re.compile(r'\b\S*https?://\S*\b', re.IGNORECASE)

# Регулярное выражение для удаления строки с городом и ссылкой
city_pattern = re.compile(r'Стежити за обстановкою в .*? можна тут - \S+', re.IGNORECASE)

# Регулярное выражение для удаления случайного набора букв (если он идёт отдельной строкой)
random_letters_pattern = re.compile(r'^\s*[а-яА-Яa-zA-Z]{4,}\s*$', re.MULTILINE)

# Текст, который добавляем в конце поста
extra_text = '🇺🇦 <a href="https://t.me/+9RxqorgcHYZkYTQy">Небесний Вартовий</a>'

@client.on(events.NewMessage(chats=source_channel_id))
async def handler(event):
    try:
        message_text = event.message.raw_text or ""  # Если текста нет, оставляем пустую строку
        message_media = event.message.media  # Получаем вложение (фото/видео)

        # Удаляем ссылки, встроенные в слова
        message_text = re.sub(url_pattern, '', message_text)

        # Удаляем строку "Стежити за обстановкою в ..."
        message_text = re.sub(city_pattern, '', message_text).strip()

        # Удаляем случайные буквы (если это отдельная строка)
        message_text = re.sub(random_letters_pattern, '', message_text).strip()

        # Проверяем на запрещенные слова и номера карт
        if any(word in message_text for word in blacklist_words) or card_pattern.search(message_text):
            print("Сообщение заблокировано из-за фильтрации.")
            return  # Игнорируем сообщение

        # Если нет текста, но есть фото – отправляем только фото
        if not message_text and message_media:
            await client.send_file(destination_channel_id, message_media)
            print("Отправлено только фото.")
            return

        # Добавляем подпись с ссылкой
        if message_text:
            message_text += f"\n\n{extra_text}"

        # Отправляем текст + фото, если они есть
        if message_media:
            await client.send_file(destination_channel_id, message_media, caption=message_text, parse_mode='html')
            print("Отправлено фото с текстом.")
        else:
            await client.send_message(destination_channel_id, message_text, link_preview=False, parse_mode='html')
            print("Отправлено текстовое сообщение.")

    except Exception as e:
        print(f"Ошибка при обработке сообщения: {e}")

client.start()
client.run_until_disconnected()

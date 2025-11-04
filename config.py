import os
from typing import List
# Токен бота от @BotFather

BOT_TOKEN = os.getenv("BOT_TOKEN")


# ID администраторов (можно получить через @userinfobot)
ADMIN_IDS = [5494287847, 6531897948]
CODES_CHANNEL = "https://t.me/proda_kod" 
# ID архив-канала (где хранятся фильмы) (например: -1001234567890)
ARCHIVE_CHANNEL_ID = -1003022803360

# Обязательные каналы для подписки (формат: {"channel_id": "@username"})
REQUIRED_CHANNELS = {
    -1002774096741: "@azyro_azart"
}



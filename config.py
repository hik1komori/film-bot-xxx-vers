import os
from typing import List
from dotenv import load_dotenv

load_dotenv() 
# Токен бота от @BotFather

BOT_TOKEN = "7361611338:AAEZ1BvOFZD_vf3Zenis2J4_SNf2TahE9u8"

# ID администраторов (можно получить через @userinfobot)
ADMIN_IDS = [7504594263, 6531897948]
CODES_CHANNEL = "https://t.me/kino_kodlari_s" 
# ID архив-канала (где хранятся фильмы) (например: -1001234567890)
ARCHIVE_CHANNEL_ID = -1003022803360

# Обязательные каналы для подписки (формат: {"channel_id": "@username"})
REQUIRED_CHANNELS = {
    -1002887536601: "@kino_kodlari_s",
    -1002992186884: "@badabumchik12"
}



import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Конфигурация бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DATA_DIR = os.getenv("DATA_DIR", "data")

# Проверяем обязательные параметры
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

if ADMIN_ID == 0:
    raise ValueError("ADMIN_ID не найден в переменных окружения")

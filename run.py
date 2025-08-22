#!/usr/bin/env python3
"""
Скрипт для запуска Telegram бота-тотализатора
"""

import sys
import os
from main import TotalizerBot

def check_requirements():
    """Проверка наличия необходимых зависимостей"""
    try:
        import telegram
        import dotenv
        return True
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("🔧 Установите зависимости командой: pip install -r requirements.txt")
        return False

def check_config():
    """Проверка конфигурации"""
    try:
        import config
        return True
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        print("🔧 Проверьте файл .env и убедитесь, что все переменные заданы")
        return False

def main():
    """Главная функция запуска"""
    print("🎲 Telegram Бот-Тотализатор")
    print("=" * 40)
    
    # Проверяем зависимости
    if not check_requirements():
        sys.exit(1)
    
    # Проверяем конфигурацию
    if not check_config():
        sys.exit(1)
    
    # Запускаем бота
    try:
        bot = TotalizerBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

#!/bin/bash

# Скрипт для запуска Telegram бота-тотализатора на Mac/Linux

echo "🎲 Запуск Telegram бота-тотализатора..."

# Проверяем наличие виртуального окружения
if [ ! -d ".venv" ]; then
    echo "❌ Виртуальное окружение не найдено"
    echo "🔧 Создаю виртуальное окружение..."
    python3 -m venv .venv
    
    echo "📦 Устанавливаю зависимости..."
    source .venv/bin/activate
    pip install -r requirements.txt
fi

# Проверяем наличие .env файла
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден"
    echo "🔧 Создайте файл .env по образцу из README.md"
    exit 1
fi

# Активируем виртуальное окружение и запускаем бота
echo "🚀 Запускаю бота..."
source .venv/bin/activate
python main.py

@echo off
chcp 65001 >nul

REM Скрипт для запуска Telegram бота-тотализатора на Windows

echo 🎲 Запуск Telegram бота-тотализатора...

REM Проверяем наличие виртуального окружения
if not exist ".venv" (
    echo ❌ Виртуальное окружение не найдено
    echo 🔧 Создаю виртуальное окружение...
    python -m venv .venv
    
    echo 📦 Устанавливаю зависимости...
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
)

REM Проверяем наличие .env файла
if not exist ".env" (
    echo ❌ Файл .env не найден
    echo 🔧 Создайте файл .env по образцу из README.md
    pause
    exit /b 1
)

REM Активируем виртуальное окружение и запускаем бота
echo 🚀 Запускаю бота...
call .venv\Scripts\activate.bat
python main.py

pause

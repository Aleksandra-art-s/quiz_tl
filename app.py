# app.py

from aiogram import executor
from bot import dp
from handlers import register_handlers  # импортируем функцию регистрации обработчиков
from database import init_db  # импортируем инициализацию базы данных

async def on_startup(_):
    await init_db()
    print("Бот запущен и готов к работе.")

# Регистрируем обработчики
register_handlers(dp)

# Запускаем бота
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

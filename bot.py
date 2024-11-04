# bot.py

from aiogram import Bot, Dispatcher
from config import API_TOKEN  # Импорт API_TOKEN из config.py
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Инициализируем бота и диспетчер
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

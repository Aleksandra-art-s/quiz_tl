# bot.py

from aiogram import Bot, Dispatcher
from config import API_TOKEN
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Инициализируем бота и диспетчер
bot = Bot(token=7645679841:AAF9Kj-r8PIyFM_vVooVDlrLMF28p4Faf9g)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

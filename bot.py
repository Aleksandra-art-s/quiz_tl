# bot.py

import logging
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import API_TOKEN

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализируем бота и диспетчер
bot = Bot(token=7645679841:AAF9Kj-r8PIyFM_vVooVDlrLMF28p4Faf9g)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

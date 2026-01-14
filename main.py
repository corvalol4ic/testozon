import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from database.db import database
from handlers.start import router as start_router
from handlers.common import router as common_router
from handlers.activation import router as activation_router  # НОВЫЙ РОУТЕР


# from handlers.echo import router as echo_router  # Убрали echo если не нужен

async def main():
    bot = Bot(token=Config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров
    dp.include_router(start_router)
    dp.include_router(activation_router)  # НОВЫЙ
    dp.include_router(common_router)
    # dp.include_router(echo_router)  # Убрали если не нужен

    # Создание таблиц в БД
    await database.create_tables()
    logging.info("✅ База данных инициализирована")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
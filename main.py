import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from database.db import database
from handlers.start import router as start_router
from handlers.common import router as common_router
from handlers.echo import router as echo_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    try:
        # Инициализация бота и диспетчера
        bot = Bot(token=Config.BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())

        # Регистрация роутеров
        dp.include_router(start_router)
        dp.include_router(common_router)
        dp.include_router(echo_router)

        # Создание таблиц в БД
        await database.create_tables()
        logger.info("✅ База данных инициализирована")

        logger.info("🤖 Бот запущен!")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
    finally:
        logger.info("🛑 Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
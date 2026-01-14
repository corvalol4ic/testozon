import asyncio
import sqlite3
from database.db import Database


async def init_db():
    """Инициализация базы данных"""
    db = Database()
    await db.create_tables()
    print("✅ База данных успешно создана!")

    # Проверим созданные таблицы
    conn = sqlite3.connect("database/data/database.db")
    cursor = conn.cursor()

    # Получим список всех таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    print("\n📊 Созданные таблицы:")
    for table in tables:
        print(f"  • {table[0]}")

    conn.close()


if __name__ == "__main__":
    asyncio.run(init_db())
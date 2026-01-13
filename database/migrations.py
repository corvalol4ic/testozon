import aiosqlite


async def run_migrations(db_path: str):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")

        # Здесь можно добавлять миграции
        # await db.execute("ALTER TABLE users ADD COLUMN new_column TEXT")

        await db.commit()
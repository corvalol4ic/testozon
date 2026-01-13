import sqlite3
import asyncio
from threading import Lock
from pathlib import Path
from config import Config
from typing import Optional, List, Tuple, Any


class Database:
    def __init__(self, db_path: str = Config.DB_PATH):
        self.db_path = db_path
        self._lock = Lock()
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Создает папку для базы данных если её нет"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Получение соединения с базой данных"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Возвращает строки как словари
        return conn

    async def create_tables(self):
        """Создание таблиц в базе данных"""

        def sync_create():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Таблица пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE,
                        username TEXT,
                        full_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Таблица сообщений
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        text TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                    )
                ''')

                # Создание индексов для ускорения запросов
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON users(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)')

                conn.commit()
                conn.close()

        await asyncio.to_thread(sync_create)
        print("✅ Таблицы в базе данных созданы")

    async def add_user(self, user_id: int, username: Optional[str], full_name: str):
        """Добавление пользователя в БД"""

        def sync_add():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
                    (user_id, username, full_name)
                )
                conn.commit()
                conn.close()

        await asyncio.to_thread(sync_add)

    async def get_user(self, user_id: int) -> Optional[dict]:
        """Получение пользователя из БД"""

        def sync_get():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM users WHERE user_id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                conn.close()
                return dict(row) if row else None

        return await asyncio.to_thread(sync_get)

    async def get_all_users(self) -> List[dict]:
        """Получение всех пользователей"""

        def sync_get_all():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]

        return await asyncio.to_thread(sync_get_all)

    async def add_message(self, user_id: int, text: str):
        """Добавление сообщения в БД"""

        def sync_add_message():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO messages (user_id, text) VALUES (?, ?)",
                    (user_id, text)
                )
                conn.commit()
                conn.close()

        await asyncio.to_thread(sync_add_message)

    async def get_user_messages(self, user_id: int, limit: int = 10) -> List[dict]:
        """Получение сообщений пользователя"""

        def sync_get_messages():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM messages WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                    (user_id, limit)
                )
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]

        return await asyncio.to_thread(sync_get_messages)

    async def get_user_count(self) -> int:
        """Получение количества пользователей"""

        def sync_get_count():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM users")
                result = cursor.fetchone()
                conn.close()
                return result['count'] if result else 0

        return await asyncio.to_thread(sync_get_count)

    async def update_user(self, user_id: int, username: Optional[str] = None, full_name: Optional[str] = None):
        """Обновление данных пользователя"""

        def sync_update():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                updates = []
                params = []

                if username is not None:
                    updates.append("username = ?")
                    params.append(username)
                if full_name is not None:
                    updates.append("full_name = ?")
                    params.append(full_name)

                if updates:
                    params.append(user_id)
                    query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
                    cursor.execute(query, params)
                    conn.commit()

                conn.close()

        await asyncio.to_thread(sync_update)


# Синглтон для работы с БД
database = Database()
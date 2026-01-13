import sqlite3
import asyncio
import secrets
import string
from threading import Lock
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union
from config import Config


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
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _generate_access_key(self, length: int = 32) -> str:
        """Генерация уникального ключа доступа"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    async def create_tables(self):
        """Создание таблиц в базе данных"""

        def sync_create():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Таблица подписок (планов)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS subscription_plans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        price REAL DEFAULT 0,
                        max_requests INTEGER DEFAULT 100,
                        duration_days INTEGER DEFAULT 30,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Основная таблица пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE NOT NULL,
                        username TEXT,
                        full_name TEXT NOT NULL,
                        access_key TEXT UNIQUE,
                        subscription_plan_id INTEGER DEFAULT 1,
                        requests_used INTEGER DEFAULT 0,
                        requests_limit INTEGER DEFAULT 100,
                        subscription_start DATE,
                        subscription_end DATE,
                        is_active BOOLEAN DEFAULT 1,
                        is_admin BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (subscription_plan_id) REFERENCES subscription_plans (id)
                    )
                ''')

                # Таблица истории подписок
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS subscription_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        plan_id INTEGER NOT NULL,
                        start_date DATE NOT NULL,
                        end_date DATE NOT NULL,
                        payment_amount REAL DEFAULT 0,
                        payment_method TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                        FOREIGN KEY (plan_id) REFERENCES subscription_plans (id)
                    )
                ''')

                # Таблица запросов/активности
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        request_type TEXT,
                        request_data TEXT,
                        response_data TEXT,
                        tokens_used INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                    )
                ''')

                # Создание индексов
                indexes = [
                    'CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)',
                    'CREATE INDEX IF NOT EXISTS idx_users_access_key ON users(access_key)',
                    'CREATE INDEX IF NOT EXISTS idx_users_subscription_end ON users(subscription_end)',
                    'CREATE INDEX IF NOT EXISTS idx_subscription_history_user_id ON subscription_history(user_id)',
                    'CREATE INDEX IF NOT EXISTS idx_user_requests_user_id ON user_requests(user_id)',
                    'CREATE INDEX IF NOT EXISTS idx_user_requests_created_at ON user_requests(created_at)'
                ]

                for index_sql in indexes:
                    cursor.execute(index_sql)

                # Создание стандартных планов подписки
                default_plans = [
                    ('FREE', 'Бесплатный план', 0, 50, 30),
                    ('BASIC', 'Базовый план', 10, 500, 30),
                    ('PRO', 'Профессиональный план', 25, 2000, 30),
                    ('PREMIUM', 'Премиум план', 50, 10000, 30),
                    ('ENTERPRISE', 'Корпоративный план', 200, 50000, 30)
                ]

                for plan in default_plans:
                    cursor.execute('''
                        INSERT OR IGNORE INTO subscription_plans 
                        (name, description, price, max_requests, duration_days) 
                        VALUES (?, ?, ?, ?, ?)
                    ''', plan)

                conn.commit()
                conn.close()

        await asyncio.to_thread(sync_create)
        print("✅ Таблицы в базе данных созданы")

    # ==================== МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ====================

    async def add_user(self, user_id: int, username: Optional[str], full_name: str) -> Dict[str, Any]:
        """Добавление пользователя в БД с автоматической генерацией ключа доступа"""

        def sync_add():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Проверяем, существует ли пользователь
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                existing_user = cursor.fetchone()

                if existing_user:
                    conn.close()
                    return dict(existing_user)

                # Генерируем уникальный ключ доступа
                access_key = self._generate_access_key()

                # Получаем ID бесплатного плана
                cursor.execute("SELECT id FROM subscription_plans WHERE name = 'FREE' LIMIT 1")
                free_plan = cursor.fetchone()
                plan_id = free_plan['id'] if free_plan else 1

                # Получаем лимиты для плана
                cursor.execute(
                    "SELECT max_requests, duration_days FROM subscription_plans WHERE id = ?",
                    (plan_id,)
                )
                plan_data = cursor.fetchone()
                requests_limit = plan_data['max_requests'] if plan_data else 100

                # Устанавливаем даты подписки
                start_date = datetime.now().date()
                end_date = start_date + timedelta(days=plan_data['duration_days'] if plan_data else 30)

                # Добавляем пользователя
                cursor.execute('''
                    INSERT INTO users 
                    (user_id, username, full_name, access_key, subscription_plan_id, 
                     requests_limit, subscription_start, subscription_end) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, username, full_name, access_key, plan_id,
                      requests_limit, start_date, end_date))

                # Получаем данные созданного пользователя
                cursor.execute(
                    "SELECT * FROM users WHERE user_id = ?",
                    (user_id,)
                )
                user = cursor.fetchone()

                # Добавляем запись в историю подписок
                if user:
                    cursor.execute('''
                        INSERT INTO subscription_history 
                        (user_id, plan_id, start_date, end_date) 
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, plan_id, start_date, end_date))

                conn.commit()
                conn.close()
                return dict(user) if user else None

        return await asyncio.to_thread(sync_add)

    async def get_user(self, user_id: int = None, access_key: str = None) -> Optional[Dict[str, Any]]:
        """Получение пользователя по user_id или access_key"""

        def sync_get():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                if user_id:
                    cursor.execute('''
                        SELECT u.*, sp.name as plan_name, sp.description as plan_description,
                               sp.price as plan_price, sp.max_requests as plan_max_requests
                        FROM users u
                        LEFT JOIN subscription_plans sp ON u.subscription_plan_id = sp.id
                        WHERE u.user_id = ?
                    ''', (user_id,))
                elif access_key:
                    cursor.execute('''
                        SELECT u.*, sp.name as plan_name, sp.description as plan_description,
                               sp.price as plan_price, sp.max_requests as plan_max_requests
                        FROM users u
                        LEFT JOIN subscription_plans sp ON u.subscription_plan_id = sp.id
                        WHERE u.access_key = ?
                    ''', (access_key,))
                else:
                    conn.close()
                    return None

                row = cursor.fetchone()
                conn.close()
                return dict(row) if row else None

        return await asyncio.to_thread(sync_get)

    async def get_all_users(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получение всех пользователей с пагинацией"""

        def sync_get_all():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT u.*, sp.name as plan_name 
                    FROM users u
                    LEFT JOIN subscription_plans sp ON u.subscription_plan_id = sp.id
                    ORDER BY u.created_at DESC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))

                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]

        return await asyncio.to_thread(sync_get_all)

    async def get_users_count(self) -> int:
        """Получение общего количества пользователей"""

        def sync_get_count():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM users")
                result = cursor.fetchone()
                conn.close()
                return result['count'] if result else 0

        return await asyncio.to_thread(sync_get_count)

    async def update_user(self, user_id: int, **kwargs) -> bool:
        """Обновление данных пользователя"""

        def sync_update():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Формируем SET часть запроса
                set_parts = []
                values = []

                allowed_fields = ['username', 'full_name', 'subscription_plan_id',
                                  'requests_used', 'requests_limit', 'subscription_start',
                                  'subscription_end', 'is_active', 'is_admin']

                for key, value in kwargs.items():
                    if key in allowed_fields:
                        set_parts.append(f"{key} = ?")
                        values.append(value)

                if not set_parts:
                    conn.close()
                    return False

                values.append(user_id)
                set_clause = ", ".join(set_parts)

                cursor.execute(f'''
                    UPDATE users 
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', values)

                conn.commit()
                conn.close()
                return cursor.rowcount > 0

        return await asyncio.to_thread(sync_update)

    async def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя"""

        def sync_delete():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                conn.commit()
                affected = cursor.rowcount
                conn.close()
                return affected > 0

        return await asyncio.to_thread(sync_delete)

    async def search_users(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Поиск пользователей по имени или username"""

        def sync_search():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                search_term = f"%{query}%"
                cursor.execute('''
                    SELECT u.*, sp.name as plan_name 
                    FROM users u
                    LEFT JOIN subscription_plans sp ON u.subscription_plan_id = sp.id
                    WHERE u.full_name LIKE ? OR u.username LIKE ?
                    ORDER BY u.created_at DESC
                    LIMIT ?
                ''', (search_term, search_term, limit))

                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]

        return await asyncio.to_thread(sync_search)

    # ==================== МЕТОДЫ ДЛЯ КЛЮЧЕЙ ДОСТУПА ====================

    async def regenerate_access_key(self, user_id: int) -> Optional[str]:
        """Регенерация ключа доступа"""

        def sync_regenerate():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                new_key = self._generate_access_key()

                cursor.execute(
                    "UPDATE users SET access_key = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (new_key, user_id)
                )

                conn.commit()
                success = cursor.rowcount > 0
                conn.close()
                return new_key if success else None

        return await asyncio.to_thread(sync_regenerate)

    async def validate_access_key(self, access_key: str) -> bool:
        """Проверка валидности ключа доступа"""

        def sync_validate():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_id FROM users WHERE access_key = ? AND is_active = 1",
                    (access_key,)
                )
                result = cursor.fetchone()
                conn.close()
                return result is not None

        return await asyncio.to_thread(sync_validate)

    # ==================== МЕТОДЫ ДЛЯ ПОДПИСОК ====================

    async def update_user_subscription(self, user_id: int, plan_name: str) -> bool:
        """Обновление подписки пользователя"""

        def sync_update():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Получаем информацию о плане
                cursor.execute(
                    "SELECT id, max_requests, duration_days FROM subscription_plans WHERE name = ?",
                    (plan_name,)
                )
                plan = cursor.fetchone()

                if not plan:
                    conn.close()
                    return False

                plan_id = plan['id']
                max_requests = plan['max_requests']
                duration_days = plan['duration_days']

                # Обновляем пользователя
                start_date = datetime.now().date()
                end_date = start_date + timedelta(days=duration_days)

                cursor.execute('''
                    UPDATE users 
                    SET subscription_plan_id = ?, 
                        requests_limit = ?,
                        requests_used = 0,
                        subscription_start = ?,
                        subscription_end = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (plan_id, max_requests, start_date, end_date, user_id))

                # Добавляем запись в историю
                cursor.execute('''
                    INSERT INTO subscription_history 
                    (user_id, plan_id, start_date, end_date) 
                    VALUES (?, ?, ?, ?)
                ''', (user_id, plan_id, start_date, end_date))

                conn.commit()
                conn.close()
                return True

        return await asyncio.to_thread(sync_update)

    async def get_all_subscription_plans(self) -> List[Dict[str, Any]]:
        """Получение всех доступных планов подписки"""

        def sync_get_plans():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT * FROM subscription_plans 
                    WHERE is_active = 1 
                    ORDER BY price ASC
                ''')

                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]

        return await asyncio.to_thread(sync_get_plans)

    async def get_subscription_plan(self, plan_id: int = None, plan_name: str = None) -> Optional[Dict[str, Any]]:
        """Получение плана подписки по ID или имени"""

        def sync_get_plan():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                if plan_id:
                    cursor.execute("SELECT * FROM subscription_plans WHERE id = ?", (plan_id,))
                elif plan_name:
                    cursor.execute("SELECT * FROM subscription_plans WHERE name = ?", (plan_name,))
                else:
                    conn.close()
                    return None

                row = cursor.fetchone()
                conn.close()
                return dict(row) if row else None

        return await asyncio.to_thread(sync_get_plan)

    # ==================== МЕТОДЫ ДЛЯ СТАТИСТИКИ ====================

    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получение статистики пользователя"""

        def sync_get_stats():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Основная информация
                cursor.execute('''
                    SELECT 
                        u.*,
                        sp.name as plan_name,
                        sp.description as plan_description,
                        sp.price as plan_price,
                        sp.max_requests as plan_max_requests,
                        (u.requests_limit - u.requests_used) as requests_remaining,
                        julianday(u.subscription_end) - julianday('now') as days_remaining
                    FROM users u
                    LEFT JOIN subscription_plans sp ON u.subscription_plan_id = sp.id
                    WHERE u.user_id = ?
                ''', (user_id,))

                user = cursor.fetchone()

                if not user:
                    conn.close()
                    return {}

                # Статистика запросов за последние 30 дней
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_requests_30d,
                        SUM(tokens_used) as total_tokens_30d
                    FROM user_requests 
                    WHERE user_id = ? 
                    AND created_at >= datetime('now', '-30 days')
                ''', (user_id,))

                requests_stats = cursor.fetchone()

                # История подписок
                cursor.execute('''
                    SELECT sh.*, sp.name as plan_name
                    FROM subscription_history sh
                    LEFT JOIN subscription_plans sp ON sh.plan_id = sp.id
                    WHERE sh.user_id = ?
                    ORDER BY sh.created_at DESC
                    LIMIT 5
                ''', (user_id,))

                subscription_history = cursor.fetchall()

                conn.close()

                result = dict(user)
                result['requests_30d'] = dict(requests_stats) if requests_stats else {}
                result['subscription_history'] = [dict(row) for row in subscription_history]

                return result

        return await asyncio.to_thread(sync_get_stats)

    async def get_system_stats(self) -> Dict[str, Any]:
        """Получение системной статистики"""

        def sync_get_system_stats():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                stats = {}

                # Общее количество пользователей
                cursor.execute("SELECT COUNT(*) as total_users FROM users")
                stats['total_users'] = cursor.fetchone()['total_users']

                # Активные пользователи
                cursor.execute("SELECT COUNT(*) as active_users FROM users WHERE is_active = 1")
                stats['active_users'] = cursor.fetchone()['active_users']

                # Пользователи по планам
                cursor.execute('''
                    SELECT sp.name as plan_name, COUNT(u.id) as count
                    FROM users u
                    LEFT JOIN subscription_plans sp ON u.subscription_plan_id = sp.id
                    GROUP BY sp.name
                ''')

                plans_stats = cursor.fetchall()
                stats['users_by_plan'] = {row['plan_name']: row['count'] for row in plans_stats}

                # Всего запросов
                cursor.execute("SELECT COUNT(*) as total_requests FROM user_requests")
                stats['total_requests'] = cursor.fetchone()['total_requests']

                # Запросы за последние 7 дней
                cursor.execute('''
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as count
                    FROM user_requests 
                    WHERE created_at >= datetime('now', '-7 days')
                    GROUP BY DATE(created_at)
                    ORDER BY date
                ''')

                requests_7d = cursor.fetchall()
                stats['requests_7d'] = [dict(row) for row in requests_7d]

                conn.close()
                return stats

        return await asyncio.to_thread(sync_get_system_stats)

    # ==================== МЕТОДЫ ДЛЯ ЗАПРОСОВ ====================

    async def increment_user_requests(self, user_id: int) -> bool:
        """Увеличение счетчика использованных запросов"""

        def sync_increment():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    "UPDATE users SET requests_used = requests_used + 1 WHERE user_id = ?",
                    (user_id,)
                )

                conn.commit()
                conn.close()
                return True

        return await asyncio.to_thread(sync_increment)

    async def add_user_request(self, user_id: int, request_type: str,
                               request_data: str, response_data: str,
                               tokens_used: int = 0):
        """Добавление записи о запросе пользователя"""

        def sync_add_request():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO user_requests 
                    (user_id, request_type, request_data, response_data, tokens_used) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, request_type, request_data, response_data, tokens_used))

                conn.commit()
                conn.close()

        await asyncio.to_thread(sync_add_request)

    async def get_user_requests(self, user_id: int, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Получение запросов пользователя"""

        def sync_get_requests():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT * FROM user_requests 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                ''', (user_id, limit, offset))

                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]

        return await asyncio.to_thread(sync_get_requests)

    # ==================== МЕТОДЫ ПРОВЕРКИ ДОСТУПА ====================

    async def check_user_access(self, user_id: int) -> Dict[str, Any]:
        """Проверка доступа пользователя"""

        def sync_check():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT 
                        u.is_active,
                        u.requests_used < u.requests_limit as has_requests,
                        u.subscription_end >= date('now') as is_subscription_active,
                        u.requests_used,
                        u.requests_limit,
                        sp.name as plan_name
                    FROM users u
                    LEFT JOIN subscription_plans sp ON u.subscription_plan_id = sp.id
                    WHERE u.user_id = ?
                ''', (user_id,))

                result = cursor.fetchone()
                conn.close()

                if not result:
                    return {
                        'has_access': False,
                        'reason': 'Пользователь не найден'
                    }

                result_dict = dict(result)
                has_access = all([
                    result_dict['is_active'],
                    result_dict['has_requests'],
                    result_dict['is_subscription_active']
                ])

                return {
                    'has_access': bool(has_access),
                    'is_active': bool(result_dict['is_active']),
                    'has_requests': bool(result_dict['has_requests']),
                    'is_subscription_active': bool(result_dict['is_subscription_active']),
                    'requests_used': result_dict['requests_used'],
                    'requests_limit': result_dict['requests_limit'],
                    'plan_name': result_dict['plan_name'],
                    'reason': 'Доступ разрешен' if has_access else 'Доступ запрещен'
                }

        return await asyncio.to_thread(sync_check)

    # ==================== АДМИНИСТРАТИВНЫЕ МЕТОДЫ ====================

    async def reset_user_requests(self, user_id: int = None):
        """Сброс счетчика запросов (для всех или одного пользователя)"""

        def sync_reset():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                if user_id:
                    cursor.execute(
                        "UPDATE users SET requests_used = 0 WHERE user_id = ?",
                        (user_id,)
                    )
                else:
                    # Сброс для всех пользователей (для крона)
                    cursor.execute("UPDATE users SET requests_used = 0")

                conn.commit()
                conn.close()

        await asyncio.to_thread(sync_reset)

    async def make_admin(self, user_id: int) -> bool:
        """Назначение пользователя администратором"""

        def sync_make_admin():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET is_admin = 1 WHERE user_id = ?",
                    (user_id,)
                )
                conn.commit()
                affected = cursor.rowcount
                conn.close()
                return affected > 0

        return await asyncio.to_thread(sync_make_admin)

    async def toggle_user_active(self, user_id: int) -> bool:
        """Переключение активности пользователя"""

        def sync_toggle():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET is_active = NOT is_active WHERE user_id = ?",
                    (user_id,)
                )
                conn.commit()
                affected = cursor.rowcount
                conn.close()
                return affected > 0

        return await asyncio.to_thread(sync_toggle)

    async def get_admins(self) -> List[Dict[str, Any]]:
        """Получение списка администраторов"""

        def sync_get_admins():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.*, sp.name as plan_name 
                    FROM users u
                    LEFT JOIN subscription_plans sp ON u.subscription_plan_id = sp.id
                    WHERE u.is_admin = 1 
                    ORDER BY u.created_at DESC
                ''')

                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]

        return await asyncio.to_thread(sync_get_admins)

    # ==================== МЕТОДЫ ОЧИСТКИ ====================

    async def cleanup_expired_subscriptions(self):
        """Очистка просроченных подписок (перевод на FREE план)"""

        def sync_cleanup():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Получаем ID FREE плана
                cursor.execute("SELECT id FROM subscription_plans WHERE name = 'FREE' LIMIT 1")
                free_plan = cursor.fetchone()

                if not free_plan:
                    conn.close()
                    return 0

                # Находим пользователей с просроченными подписками
                cursor.execute('''
                    SELECT user_id FROM users 
                    WHERE subscription_end < date('now') 
                    AND subscription_plan_id != ?
                ''', (free_plan['id'],))

                expired_users = cursor.fetchall()
                count = 0

                for user in expired_users:
                    cursor.execute('''
                        UPDATE users 
                        SET subscription_plan_id = ?,
                            requests_limit = (SELECT max_requests FROM subscription_plans WHERE id = ?),
                            subscription_start = date('now'),
                            subscription_end = date('now', '+30 days'),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    ''', (free_plan['id'], free_plan['id'], user['user_id']))

                    # Добавляем запись в историю
                    cursor.execute('''
                        INSERT INTO subscription_history 
                        (user_id, plan_id, start_date, end_date) 
                        VALUES (?, ?, date('now'), date('now', '+30 days'))
                    ''', (user['user_id'], free_plan['id']))

                    count += 1

                conn.commit()
                conn.close()
                return count

        return await asyncio.to_thread(sync_cleanup)


# Синглтон для работы с БД
database = Database()
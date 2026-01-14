import sqlite3
import asyncio
import secrets
import string
import hashlib
from threading import Lock
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
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

    def _generate_activation_key(self, length: int = 20) -> str:
        """Генерация ключа активации"""
        alphabet = string.ascii_uppercase + string.digits
        # Убираем похожие символы (0/O, 1/I/L)
        alphabet = alphabet.replace('0', '').replace('O', '').replace('1', '').replace('I', '').replace('L', '')
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def _hash_key(self, key: str) -> str:
        """Хеширование ключа для безопасного хранения"""
        return hashlib.sha256(key.encode()).hexdigest()

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
                        max_activation_keys INTEGER DEFAULT 1,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Таблица ключей активации
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS activation_keys (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key_hash TEXT UNIQUE NOT NULL,
                        plan_id INTEGER NOT NULL,
                        key_code TEXT UNIQUE NOT NULL,
                        is_used BOOLEAN DEFAULT 0,
                        used_by_user_id INTEGER,
                        used_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        FOREIGN KEY (plan_id) REFERENCES subscription_plans (id)
                    )
                ''')

                # Основная таблица пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE NOT NULL,
                        username TEXT,
                        full_name TEXT NOT NULL,
                        subscription_plan_id INTEGER DEFAULT 1,
                        activation_key_id INTEGER,
                        requests_used INTEGER DEFAULT 0,
                        requests_limit INTEGER DEFAULT 100,
                        subscription_start DATE,
                        subscription_end DATE,
                        is_active BOOLEAN DEFAULT 1,
                        is_admin BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (subscription_plan_id) REFERENCES subscription_plans (id),
                        FOREIGN KEY (activation_key_id) REFERENCES activation_keys (id)
                    )
                ''')

                # Таблица истории подписок
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS subscription_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        plan_id INTEGER NOT NULL,
                        activation_key_id INTEGER,
                        start_date DATE NOT NULL,
                        end_date DATE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                        FOREIGN KEY (plan_id) REFERENCES subscription_plans (id),
                        FOREIGN KEY (activation_key_id) REFERENCES activation_keys (id)
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

                # Таблица ссылок пользователя
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_links (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        url TEXT NOT NULL,
                        title TEXT,
                        description TEXT,
                        category TEXT DEFAULT 'general',
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                    )
                ''')

                # Создание индексов
                indexes = [
                    'CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)',
                    'CREATE INDEX IF NOT EXISTS idx_users_activation_key ON users(activation_key_id)',
                    'CREATE INDEX IF NOT EXISTS idx_activation_keys_key_hash ON activation_keys(key_hash)',
                    'CREATE INDEX IF NOT EXISTS idx_activation_keys_key_code ON activation_keys(key_code)',
                    'CREATE INDEX IF NOT EXISTS idx_activation_keys_is_used ON activation_keys(is_used)',
                    'CREATE INDEX IF NOT EXISTS idx_users_subscription_end ON users(subscription_end)',
                    'CREATE INDEX IF NOT EXISTS idx_subscription_history_user_id ON subscription_history(user_id)',
                    'CREATE INDEX IF NOT EXISTS idx_user_requests_user_id ON user_requests(user_id)',
                    'CREATE INDEX IF NOT EXISTS idx_user_links_user_id ON user_links(user_id)',
                    'CREATE INDEX IF NOT EXISTS idx_user_links_category ON user_links(category)',
                    'CREATE INDEX IF NOT EXISTS idx_user_links_is_active ON user_links(is_active)'
                ]

                for index_sql in indexes:
                    cursor.execute(index_sql)

                # Создание стандартных планов подписки с количеством ключей
                default_plans = [
                    ('FREE', 'Бесплатный план', 0, 50, 30, 0),
                    ('BASIC', 'Базовый план', 10, 500, 30, 1),
                    ('PRO', 'Профессиональный план', 25, 2000, 30, 3),
                    ('PREMIUM', 'Премиум план', 50, 10000, 30, 5),
                    ('ENTERPRISE', 'Корпоративный план', 200, 50000, 30, 10)
                ]

                for plan in default_plans:
                    cursor.execute('''
                        INSERT OR IGNORE INTO subscription_plans 
                        (name, description, price, max_requests, duration_days, max_activation_keys) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', plan)

                conn.commit()
                conn.close()

        await asyncio.to_thread(sync_create)
        print("✅ Таблицы в базе данных созданы")

    # ==================== МЕТОДЫ ДЛЯ КЛЮЧЕЙ АКТИВАЦИИ ====================

    async def generate_activation_keys(self, plan_name: str, quantity: int = 1,
                                       expires_in_days: int = 365) -> List[str]:
        """Генерация ключей активации для плана"""

        def sync_generate():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Получаем ID плана
                cursor.execute(
                    "SELECT id FROM subscription_plans WHERE name = ?",
                    (plan_name,)
                )
                plan = cursor.fetchone()

                if not plan:
                    conn.close()
                    return []

                plan_id = plan['id']
                keys = []

                for _ in range(quantity):
                    key_code = self._generate_activation_key()
                    key_hash = self._hash_key(key_code)
                    expires_at = datetime.now() + timedelta(days=expires_in_days)

                    try:
                        cursor.execute('''
                            INSERT INTO activation_keys 
                            (key_hash, plan_id, key_code, expires_at) 
                            VALUES (?, ?, ?, ?)
                        ''', (key_hash, plan_id, key_code, expires_at))
                        keys.append(key_code)
                    except sqlite3.IntegrityError:
                        # Если ключ неуникальный, пропускаем
                        continue

                conn.commit()
                conn.close()
                return keys

        return await asyncio.to_thread(sync_generate)

    async def activate_key(self, user_id: int, key_code: str) -> Dict[str, Any]:
        """Активация ключа пользователем с защитой от повторного использования"""

        def sync_activate():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Получаем информацию о ключе
                cursor.execute('''
                    SELECT ak.*, sp.name as plan_name, sp.max_requests, sp.duration_days
                    FROM activation_keys ak
                    JOIN subscription_plans sp ON ak.plan_id = sp.id
                    WHERE ak.key_code = ? 
                    AND (ak.expires_at IS NULL OR ak.expires_at > CURRENT_TIMESTAMP)
                ''', (key_code,))

                key_data = cursor.fetchone()

                if not key_data:
                    conn.close()
                    return {
                        'success': False,
                        'error': 'Ключ не найден или просрочен'
                    }

                key_id = key_data['id']

                # Проверяем, использован ли ключ
                if key_data['is_used']:
                    # Проверяем, привязан ли ключ к этому пользователю
                    if key_data['used_by_user_id'] == user_id:
                        conn.close()
                        return {
                            'success': False,
                            'error': 'Этот ключ уже активирован на вашем аккаунте'
                        }
                    else:
                        conn.close()
                        return {
                            'success': False,
                            'error': 'Ключ уже использован другим пользователем'
                        }

                plan_id = key_data['plan_id']
                plan_name = key_data['plan_name']
                max_requests = key_data['max_requests']
                duration_days = key_data['duration_days']

                # Проверяем, есть ли уже пользователь
                cursor.execute(
                    "SELECT * FROM users WHERE user_id = ?",
                    (user_id,)
                )
                user = cursor.fetchone()

                if not user:
                    conn.close()
                    return {
                        'success': False,
                        'error': 'Сначала зарегистрируйтесь через /start'
                    }

                # Проверяем, не активирован ли уже ключ у этого пользователя
                cursor.execute(
                    "SELECT activation_key_id FROM users WHERE user_id = ? AND activation_key_id IS NOT NULL",
                    (user_id,)
                )
                existing_key = cursor.fetchone()

                if existing_key:
                    conn.close()
                    return {
                        'success': False,
                        'error': 'У вас уже активирован ключ. Сначала отключите текущий.'
                    }

                # Устанавливаем даты подписки
                start_date = datetime.now().date()
                end_date = start_date + timedelta(days=duration_days)

                # Обновляем пользователя
                cursor.execute('''
                    UPDATE users 
                    SET subscription_plan_id = ?,
                        activation_key_id = ?,
                        requests_limit = ?,
                        requests_used = 0,
                        subscription_start = ?,
                        subscription_end = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (plan_id, key_id, max_requests, start_date, end_date, user_id))

                # Помечаем ключ как использованный и привязываем к пользователю
                cursor.execute('''
                    UPDATE activation_keys 
                    SET is_used = 1, 
                        used_by_user_id = ?, 
                        used_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (user_id, key_id))

                # Добавляем запись в историю подписок
                cursor.execute('''
                    INSERT INTO subscription_history 
                    (user_id, plan_id, activation_key_id, start_date, end_date) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, plan_id, key_id, start_date, end_date))

                conn.commit()
                conn.close()

                return {
                    'success': True,
                    'plan_name': plan_name,
                    'max_requests': max_requests,
                    'start_date': start_date,
                    'end_date': end_date,
                    'duration_days': duration_days,
                    'key_id': key_id
                }

        return await asyncio.to_thread(sync_activate)

    async def validate_key(self, key_code: str) -> Dict[str, Any]:
        """Проверка ключа с информацией о использовании"""

        def sync_validate():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT ak.*, sp.name as plan_name, sp.description, 
                           sp.max_requests, sp.duration_days, sp.price,
                           u.user_id as used_by_id, u.username, u.full_name
                    FROM activation_keys ak
                    JOIN subscription_plans sp ON ak.plan_id = sp.id
                    LEFT JOIN users u ON ak.used_by_user_id = u.user_id
                    WHERE ak.key_code = ?
                ''', (key_code,))

                key_data = cursor.fetchone()

                if not key_data:
                    conn.close()
                    return {'valid': False, 'error': 'Ключ не найден'}

                key_dict = dict(key_data)

                # Проверяем статус ключа
                if key_dict['is_used']:
                    if key_dict['used_by_id']:
                        used_by = f"пользователем {key_dict['full_name']} (@{key_dict['username'] or 'нет'})"
                    else:
                        used_by = "другим пользователем"
                    conn.close()
                    return {
                        'valid': False,
                        'error': f'Ключ уже использован {used_by}',
                        'used_by_user_id': key_dict['used_by_id'],
                        'used_by_username': key_dict['username'],
                        'used_by_full_name': key_dict['full_name']
                    }

                if key_dict['expires_at'] and datetime.fromisoformat(key_dict['expires_at']) < datetime.now():
                    conn.close()
                    return {'valid': False, 'error': 'Ключ просрочен'}

                conn.close()
                return {
                    'valid': True,
                    'plan_name': key_dict['plan_name'],
                    'description': key_dict['description'],
                    'max_requests': key_dict['max_requests'],
                    'duration_days': key_dict['duration_days'],
                    'price': key_dict['price'],
                    'created_at': key_dict['created_at'],
                    'expires_at': key_dict['expires_at'],
                    'is_used': key_dict['is_used']
                }

        return await asyncio.to_thread(sync_validate)

    async def deactivate_user_key(self, user_id: int) -> bool:
        """Отвязка ключа от пользователя (перевод на FREE план)"""

        def sync_deactivate():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Получаем текущий ключ пользователя
                cursor.execute(
                    "SELECT activation_key_id FROM users WHERE user_id = ?",
                    (user_id,)
                )
                user_data = cursor.fetchone()

                if not user_data or not user_data['activation_key_id']:
                    conn.close()
                    return False

                key_id = user_data['activation_key_id']

                # Получаем ID FREE плана
                cursor.execute("SELECT id, max_requests FROM subscription_plans WHERE name = 'FREE'")
                free_plan = cursor.fetchone()

                if not free_plan:
                    conn.close()
                    return False

                # Обновляем пользователя на FREE план
                start_date = datetime.now().date()
                end_date = start_date + timedelta(days=30)

                cursor.execute('''
                    UPDATE users 
                    SET subscription_plan_id = ?,
                        activation_key_id = NULL,
                        requests_limit = ?,
                        subscription_start = ?,
                        subscription_end = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (free_plan['id'], free_plan['max_requests'], start_date, end_date, user_id))

                # Ключ остается использованным и не может быть использован повторно

                # Добавляем запись в историю подписок
                cursor.execute('''
                    INSERT INTO subscription_history 
                    (user_id, plan_id, start_date, end_date) 
                    VALUES (?, ?, ?, ?)
                ''', (user_id, free_plan['id'], start_date, end_date))

                conn.commit()
                conn.close()
                return True

        return await asyncio.to_thread(sync_deactivate)

    async def get_user_active_key(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение активного ключа пользователя"""

        def sync_get_key():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT ak.*, sp.name as plan_name
                    FROM users u
                    JOIN activation_keys ak ON u.activation_key_id = ak.id
                    JOIN subscription_plans sp ON ak.plan_id = sp.id
                    WHERE u.user_id = ? AND ak.is_used = 1
                ''', (user_id,))

                key_data = cursor.fetchone()
                conn.close()
                return dict(key_data) if key_data else None

        return await asyncio.to_thread(sync_get_key)

    async def get_all_keys(self, plan_name: str = None, used: bool = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Получение всех ключей с фильтрацией"""

        def sync_get_keys():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                query = '''
                    SELECT ak.*, sp.name as plan_name, sp.max_requests,
                           u.user_id as used_by_id, u.username, u.full_name
                    FROM activation_keys ak
                    JOIN subscription_plans sp ON ak.plan_id = sp.id
                    LEFT JOIN users u ON ak.used_by_user_id = u.user_id
                '''

                params = []
                conditions = []

                if plan_name:
                    conditions.append("sp.name = ?")
                    params.append(plan_name)

                if used is not None:
                    conditions.append("ak.is_used = ?")
                    params.append(1 if used else 0)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                query += " ORDER BY ak.created_at DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]

        return await asyncio.to_thread(sync_get_keys)

    async def is_key_linked_to_user(self, user_id: int, key_code: str) -> bool:
        """Проверка, привязан ли ключ к пользователю"""

        def sync_check():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT COUNT(*) as count 
                    FROM activation_keys ak
                    JOIN users u ON ak.id = u.activation_key_id
                    WHERE ak.key_code = ? AND u.user_id = ?
                ''', (key_code, user_id))

                result = cursor.fetchone()
                conn.close()
                return result['count'] > 0 if result else False

        return await asyncio.to_thread(sync_check)

    # ==================== МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ====================

    async def add_user(self, user_id: int, username: Optional[str], full_name: str) -> Dict[str, Any]:
        """Добавление пользователя в БД"""

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

                # Получаем ID бесплатного плана
                cursor.execute("SELECT id, max_requests FROM subscription_plans WHERE name = 'FREE' LIMIT 1")
                free_plan = cursor.fetchone()

                if not free_plan:
                    conn.close()
                    return {}

                plan_id = free_plan['id']
                requests_limit = free_plan['max_requests']

                # Устанавливаем даты подписки
                start_date = datetime.now().date()
                end_date = start_date + timedelta(days=30)

                # Добавляем пользователя
                cursor.execute('''
                    INSERT INTO users 
                    (user_id, username, full_name, subscription_plan_id, 
                     requests_limit, subscription_start, subscription_end) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, username, full_name, plan_id,
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

    async def get_user(self, user_id: int = None) -> Optional[Dict[str, Any]]:
        """Получение пользователя с информацией о ключе"""

        def sync_get():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                if user_id:
                    cursor.execute('''
                        SELECT 
                            u.*, 
                            sp.name as plan_name, 
                            sp.description as plan_description,
                            sp.price as plan_price, 
                            sp.max_requests as plan_max_requests,
                            ak.key_code as activation_key,
                            ak.created_at as key_created_at
                        FROM users u
                        LEFT JOIN subscription_plans sp ON u.subscription_plan_id = sp.id
                        LEFT JOIN activation_keys ak ON u.activation_key_id = ak.id
                        WHERE u.user_id = ?
                    ''', (user_id,))
                else:
                    conn.close()
                    return None

                row = cursor.fetchone()
                conn.close()
                return dict(row) if row else None

        return await asyncio.to_thread(sync_get)

    async def get_all_users(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получение всех пользователей"""

        def sync_get_all():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.*, sp.name as plan_name, ak.key_code as activation_key
                    FROM users u
                    LEFT JOIN subscription_plans sp ON u.subscription_plan_id = sp.id
                    LEFT JOIN activation_keys ak ON u.activation_key_id = ak.id
                    ORDER BY u.created_at DESC LIMIT ? OFFSET ?
                ''', (limit, offset))
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]

        return await asyncio.to_thread(sync_get_all)

    async def get_users_count(self) -> int:
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
                    return {'has_access': False, 'reason': 'Пользователь не найден'}
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

    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получение статистики пользователя"""

        def sync_get_stats():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        u.*,
                        sp.name as plan_name,
                        sp.description as plan_description,
                        sp.price as plan_price,
                        sp.max_requests as plan_max_requests,
                        (u.requests_limit - u.requests_used) as requests_remaining,
                        julianday(u.subscription_end) - julianday('now') as days_remaining,
                        ak.key_code as activation_key
                    FROM users u
                    LEFT JOIN subscription_plans sp ON u.subscription_plan_id = sp.id
                    LEFT JOIN activation_keys ak ON u.activation_key_id = ak.id
                    WHERE u.user_id = ?
                ''', (user_id,))
                user = cursor.fetchone()
                if not user:
                    conn.close()
                    return {}
                result = dict(user)
                conn.close()
                return result

        return await asyncio.to_thread(sync_get_stats)

    async def get_all_subscription_plans(self) -> List[Dict[str, Any]]:
        """Получение всех планов подписки"""

        def sync_get_plans():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM subscription_plans WHERE is_active = 1 ORDER BY price ASC')
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]

        return await asyncio.to_thread(sync_get_plans)

    # ==================== МЕТОДЫ ДЛЯ ССЫЛОК ====================

    async def add_user_link(self, user_id: int, url: str, title: str = None,
                            description: str = None, category: str = 'general') -> int:
        """Добавление ссылки пользователя"""

        def sync_add_link():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO user_links 
                    (user_id, url, title, description, category) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, url, title, description, category))

                link_id = cursor.lastrowid
                conn.commit()
                conn.close()
                return link_id

        return await asyncio.to_thread(sync_add_link)

    async def get_user_links(self, user_id: int, category: str = None,
                             limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Получение ссылок пользователя"""

        def sync_get_links():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                query = '''
                    SELECT * FROM user_links 
                    WHERE user_id = ? AND is_active = 1
                '''
                params = [user_id]

                if category:
                    query += " AND category = ?"
                    params.append(category)

                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor.execute(query, params)
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]

        return await asyncio.to_thread(sync_get_links)

    async def get_user_link_count(self, user_id: int, category: str = None) -> int:
        """Получение количества ссылок пользователя"""

        def sync_get_count():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                query = "SELECT COUNT(*) as count FROM user_links WHERE user_id = ? AND is_active = 1"
                params = [user_id]

                if category:
                    query += " AND category = ?"
                    params.append(category)

                cursor.execute(query, params)
                result = cursor.fetchone()
                conn.close()
                return result['count'] if result else 0

        return await asyncio.to_thread(sync_get_count)

    async def get_link_categories(self, user_id: int) -> List[str]:
        """Получение категорий ссылок пользователя"""

        def sync_get_categories():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT DISTINCT category 
                    FROM user_links 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY category
                ''', (user_id,))

                rows = cursor.fetchall()
                conn.close()
                return [row['category'] for row in rows]

        return await asyncio.to_thread(sync_get_categories)

    async def search_user_links(self, user_id: int, search_query: str,
                                limit: int = 20) -> List[Dict[str, Any]]:
        """Поиск ссылок пользователя"""

        def sync_search_links():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                search_term = f"%{search_query}%"
                cursor.execute('''
                    SELECT * FROM user_links 
                    WHERE user_id = ? AND is_active = 1 
                    AND (url LIKE ? OR title LIKE ? OR description LIKE ? OR category LIKE ?)
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (user_id, search_term, search_term, search_term, search_term, limit))

                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]

        return await asyncio.to_thread(sync_search_links)

    async def delete_user_link(self, link_id: int, user_id: int = None) -> bool:
        """Удаление ссылки пользователя"""

        def sync_delete_link():
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                query = "UPDATE user_links SET is_active = 0 WHERE id = ?"
                params = [link_id]

                if user_id:
                    query += " AND user_id = ?"
                    params.append(user_id)

                cursor.execute(query, params)
                conn.commit()
                success = cursor.rowcount > 0
                conn.close()
                return success

        return await asyncio.to_thread(sync_delete_link)


# Синглтон для работы с БД
database = Database()
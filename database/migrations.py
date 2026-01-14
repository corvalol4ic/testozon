import sqlite3
import os
from pathlib import Path


def migrate_database():
    db_path = "data/database.db"

    if not os.path.exists(db_path):
        print(f"❌ База данных {db_path} не найдена!")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Проверяем существующие колонки в таблице users
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]

        print(f"📋 Существующие колонки в users: {columns}")

        # Добавляем недостающие колонки
        if 'activation_key_id' not in columns:
            print("➕ Добавляем колонку activation_key_id в users")
            cursor.execute('''
                ALTER TABLE users 
                ADD COLUMN activation_key_id INTEGER 
                REFERENCES activation_keys (id)
            ''')

        # Проверяем таблицу subscription_history
        cursor.execute("PRAGMA table_info(subscription_history)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'activation_key_id' not in columns:
            print("➕ Добавляем колонку activation_key_id в subscription_history")
            cursor.execute('''
                ALTER TABLE subscription_history 
                ADD COLUMN activation_key_id INTEGER 
                REFERENCES activation_keys (id)
            ''')

        # Проверяем существование таблицы activation_keys
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='activation_keys'")
        if not cursor.fetchone():
            print("➕ Создаем таблицу activation_keys")
            cursor.execute('''
                CREATE TABLE activation_keys (
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

            # Создаем индексы
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_activation_keys_key_hash ON activation_keys(key_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_activation_keys_key_code ON activation_keys(key_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_activation_keys_is_used ON activation_keys(is_used)')

        # Проверяем таблицу subscription_plans
        cursor.execute("PRAGMA table_info(subscription_plans)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'max_activation_keys' not in columns:
            print("➕ Добавляем колонку max_activation_keys в subscription_plans")
            cursor.execute('''
                ALTER TABLE subscription_plans 
                ADD COLUMN max_activation_keys INTEGER DEFAULT 1
            ''')

            # Обновляем значения для существующих планов
            cursor.execute("UPDATE subscription_plans SET max_activation_keys = 0 WHERE name = 'FREE'")
            cursor.execute("UPDATE subscription_plans SET max_activation_keys = 1 WHERE name = 'BASIC'")
            cursor.execute("UPDATE subscription_plans SET max_activation_keys = 3 WHERE name = 'PRO'")
            cursor.execute("UPDATE subscription_plans SET max_activation_keys = 5 WHERE name = 'PREMIUM'")
            cursor.execute("UPDATE subscription_plans SET max_activation_keys = 10 WHERE name = 'ENTERPRISE'")

        conn.commit()
        print("✅ Миграция успешно завершена!")
        return True

    except sqlite3.Error as e:
        print(f"❌ Ошибка при миграции: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def recreate_database():
    """Полностью пересоздать базу данных"""
    db_path = "data/database.db"

    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup"
        os.rename(db_path, backup_path)
        print(f"📁 Создана резервная копия: {backup_path}")

    # Создаем папку если ее нет
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Создаем таблицы с правильной структурой
    print("🔄 Создаем новую базу данных...")

    # Таблица подписок (планов)
    cursor.execute('''
        CREATE TABLE subscription_plans (
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
        CREATE TABLE activation_keys (
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
        CREATE TABLE users (
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
        CREATE TABLE subscription_history (
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
        CREATE TABLE user_requests (
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
        'CREATE INDEX idx_users_user_id ON users(user_id)',
        'CREATE INDEX idx_users_activation_key ON users(activation_key_id)',
        'CREATE INDEX idx_activation_keys_key_hash ON activation_keys(key_hash)',
        'CREATE INDEX idx_activation_keys_key_code ON activation_keys(key_code)',
        'CREATE INDEX idx_activation_keys_is_used ON activation_keys(is_used)',
        'CREATE INDEX idx_users_subscription_end ON users(subscription_end)',
        'CREATE INDEX idx_subscription_history_user_id ON subscription_history(user_id)',
        'CREATE INDEX idx_user_requests_user_id ON user_requests(user_id)'
    ]

    for index_sql in indexes:
        cursor.execute(index_sql)

    # Создание стандартных планов подписки
    default_plans = [
        ('FREE', 'Бесплатный план', 0, 50, 30, 0),
        ('BASIC', 'Базовый план', 10, 500, 30, 1),
        ('PRO', 'Профессиональный план', 25, 2000, 30, 3),
        ('PREMIUM', 'Премиум план', 50, 10000, 30, 5),
        ('ENTERPRISE', 'Корпоративный план', 200, 50000, 30, 10)
    ]

    for plan in default_plans:
        cursor.execute('''
            INSERT INTO subscription_plans 
            (name, description, price, max_requests, duration_days, max_activation_keys) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', plan)

    conn.commit()
    conn.close()

    print("✅ Новая база данных успешно создана!")
    return True


if __name__ == "__main__":
    import sys

    print("🛠️  Мигратор базы данных")
    print("=" * 50)

    if len(sys.argv) > 1 and sys.argv[1] == "--recreate":
        print("Выбран режим полного пересоздания базы данных")
        if input("⚠️  Вы уверены? Все данные будут удалены! (y/N): ").lower() == 'y':
            recreate_database()
        else:
            print("❌ Отменено")
    else:
        print("Выбран режим миграции (добавление недостающих колонок)")
        if migrate_database():
            print("\n✅ База данных готова к работе!")
        else:
            print("\n❌ Произошла ошибка. Попробуйте пересоздать базу:")
            print("   python migrate_database.py --recreate")
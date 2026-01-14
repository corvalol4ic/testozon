import sqlite3
import secrets
import string
import hashlib
from datetime import datetime, timedelta
from pathlib import Path


def create_tables_if_not_exist(db_path: str = "data/database.db"):
    """Создание таблиц если их нет"""
    # Создаем папку если ее нет
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
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

    # Таблица ключей активации - ПРАВИЛЬНАЯ СТРУКТУРА
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

    # Таблица пользователей (минимальная версия для генератора ключей)
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

    # Проверяем наличие колонки expires_at
    cursor.execute("PRAGMA table_info(activation_keys)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'expires_at' not in columns:
        print("➕ Добавляем колонку expires_at в таблицу activation_keys")
        cursor.execute('''
            ALTER TABLE activation_keys 
            ADD COLUMN expires_at TIMESTAMP
        ''')

    # Проверяем наличие колонки max_activation_keys в subscription_plans
    cursor.execute("PRAGMA table_info(subscription_plans)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'max_activation_keys' not in columns:
        print("➕ Добавляем колонку max_activation_keys в таблицу subscription_plans")
        cursor.execute('''
            ALTER TABLE subscription_plans 
            ADD COLUMN max_activation_keys INTEGER DEFAULT 1
        ''')

    # Создаем стандартные планы если их нет
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
    print("✅ Таблицы созданы/проверены")


def get_plan_id_by_name(plan_name: str, db_path: str = "data/database.db") -> int:
    """Получение ID плана по имени"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM subscription_plans WHERE name = ?",
        (plan_name.upper(),)
    )

    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0]
    else:
        # Возвращаем ID BASIC плана по умолчанию
        return 2  # BASIC


def generate_key(plan_name: str = "BASIC", quantity: int = 1,
                 expires_in_days: int = 365, db_path: str = "data/database.db") -> list:
    """Генерация ключей активации"""

    # Создаем таблицы если их нет
    create_tables_if_not_exist(db_path)

    # Получаем ID плана
    plan_id = get_plan_id_by_name(plan_name, db_path)

    # Алфавит для генерации ключей (без похожих символов)
    alphabet = string.ascii_uppercase + string.digits
    alphabet = alphabet.replace('0', '').replace('O', '').replace('1', '').replace('I', '').replace('L', '')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    generated_keys = []

    for i in range(quantity):
        # Пробуем сгенерировать уникальный ключ
        for attempt in range(10):  # 10 попыток
            # Генерируем ключ формата XXXX-XXXX-XXXX-XXXX
            key_parts = []
            for _ in range(4):
                key_parts.append(''.join(secrets.choice(alphabet) for _ in range(4)))
            key_code = '-'.join(key_parts)

            # Хешируем для хранения
            key_hash = hashlib.sha256(key_code.encode()).hexdigest()

            # Устанавливаем срок действия (может быть None для бессрочных)
            expires_at = None
            if expires_in_days > 0:
                expires_at = datetime.now() + timedelta(days=expires_in_days)

            try:
                cursor.execute('''
                    INSERT INTO activation_keys 
                    (key_hash, plan_id, key_code, expires_at) 
                    VALUES (?, ?, ?, ?)
                ''', (key_hash, plan_id, key_code, expires_at))

                generated_keys.append(key_code)
                print(f"✅ Сгенерирован ключ #{i + 1}: {key_code} (план: {plan_name})")
                break  # Успешно, выходим из попыток

            except sqlite3.IntegrityError as e:
                if attempt == 9:  # Последняя попытка
                    print(f"❌ Не удалось сгенерировать уникальный ключ после 10 попыток: {e}")
                continue  # Пробуем снова

    conn.commit()

    # Получаем информацию о плане
    cursor.execute(
        "SELECT name, max_requests, duration_days, price FROM subscription_plans WHERE id = ?",
        (plan_id,)
    )
    plan_info = cursor.fetchone()

    conn.close()

    return generated_keys, plan_info


def list_keys(plan_name: str = None, show_used: bool = False,
              limit: int = 20, db_path: str = "data/database.db"):
    """Просмотр сгенерированных ключей"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = '''
        SELECT ak.key_code, ak.is_used, ak.created_at, ak.expires_at, 
               sp.name as plan_name, u.username, u.full_name
        FROM activation_keys ak
        JOIN subscription_plans sp ON ak.plan_id = sp.id
        LEFT JOIN users u ON ak.used_by_user_id = u.user_id
    '''

    params = []

    if plan_name:
        query += " WHERE sp.name = ?"
        params.append(plan_name.upper())

        if not show_used:
            query += " AND ak.is_used = 0"
    elif not show_used:
        query += " WHERE ak.is_used = 0"

    query += " ORDER BY ak.created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    keys = cursor.fetchall()

    print(f"\n📋 Список ключей:")
    if plan_name:
        print(f"План: {plan_name}")
    print("-" * 50)

    for key in keys:
        status = "✅ НОВЫЙ" if not key[1] else "❌ ИСПОЛЬЗОВАН"
        used_by = f"👤 {key[6]} (@{key[5]})" if key[1] else ""
        expires = f" | 📅 {key[3][:10]}" if key[3] else " | ⏳ Бессрочный"

        print(f"{status} | {key[0]} | План: {key[4]}{expires} {used_by}")

    conn.close()


def get_key_stats(db_path: str = "data/database.db"):
    """Статистика ключей"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Общая статистика
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_used = 1 THEN 1 ELSE 0 END) as used,
            SUM(CASE WHEN is_used = 0 THEN 1 ELSE 0 END) as new
        FROM activation_keys
    ''')
    total_stats = cursor.fetchone()

    # Статистика по планам
    cursor.execute('''
        SELECT 
            sp.name,
            COUNT(*) as total,
            SUM(CASE WHEN ak.is_used = 1 THEN 1 ELSE 0 END) as used
        FROM activation_keys ak
        JOIN subscription_plans sp ON ak.plan_id = sp.id
        GROUP BY sp.name
        ORDER BY sp.price
    ''')
    plan_stats = cursor.fetchall()

    print("\n📊 Статистика ключей:")
    print("-" * 50)
    print(f"Всего ключей: {total_stats[0]}")
    print(f"Использовано: {total_stats[1]}")
    print(f"Доступно: {total_stats[2]}")

    print("\n💎 По планам:")
    for stat in plan_stats:
        print(f"  {stat[0]}: {stat[2]}/{stat[1]} (использовано/всего)")

    conn.close()


def recreate_database(db_path: str = "data/database.db"):
    """Полностью пересоздать базу данных"""
    # Удаляем старую базу если есть
    if Path(db_path).exists():
        Path(db_path).unlink()
        print(f"🗑️  Удалена старая база данных")

    # Создаем папку если ее нет
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

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

    # Таблица ключей активации - ПРАВИЛЬНАЯ СТРУКТУРА
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

    # Создаем стандартные планы подписки
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
    import argparse

    parser = argparse.ArgumentParser(description="Генератор ключей активации")
    parser.add_argument("action", choices=["generate", "list", "stats", "recreate"],
                        help="Действие: generate - создать ключи, list - список, stats - статистика, recreate - пересоздать базу")
    parser.add_argument("--plan", default="BASIC",
                        help="Название плана (FREE, BASIC, PRO, PREMIUM, ENTERPRISE)")
    parser.add_argument("--quantity", type=int, default=1,
                        help="Количество ключей для генерации")
    parser.add_argument("--expires", type=int, default=365,
                        help="Срок действия ключей в днях (0 = бессрочно)")
    parser.add_argument("--used", action="store_true",
                        help="Показывать использованные ключи (только для list)")
    parser.add_argument("--limit", type=int, default=20,
                        help="Лимит для списка ключей")

    args = parser.parse_args()

    if args.action == "recreate":
        if input("⚠️  Вы уверены? Все данные будут удалены! (y/N): ").lower() == 'y':
            recreate_database()
        else:
            print("❌ Отменено")

    elif args.action == "generate":
        keys, plan_info = generate_key(
            plan_name=args.plan,
            quantity=args.quantity,
            expires_in_days=args.expires
        )

        if keys:
            print(f"\n🎉 Успешно сгенерировано {len(keys)} ключей:")
            print(f"💎 План: {plan_info[0]}")
            print(f"📊 Лимит запросов: {plan_info[1]}/мес")
            print(f"📅 Длительность: {plan_info[2]} дней")
            print(f"💰 Цена: {plan_info[3]}$")
            print(f"📅 Срок действия ключей: {args.expires if args.expires > 0 else 'бессрочно'} дней")
            print("\n🔑 Ключи:")
            for key in keys:
                print(f"  {key}")

            # Сохраняем ключи в файл
            if keys:
                filename = f"keys_{args.plan}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"План: {plan_info[0]}\n")
                    f.write(f"Лимит запросов: {plan_info[1]}/мес\n")
                    f.write(f"Длительность: {plan_info[2]} дней\n")
                    f.write(f"Цена: {plan_info[3]}$\n")
                    f.write(f"Срок действия: {args.expires if args.expires > 0 else 'бессрочно'} дней\n")
                    f.write(f"Дата генерации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 40 + "\n")
                    for key in keys:
                        f.write(f"{key}\n")
                print(f"\n💾 Ключи сохранены в файл: {filename}")

    elif args.action == "list":
        list_keys(
            plan_name=args.plan,
            show_used=args.used,
            limit=args.limit
        )

    elif args.action == "stats":
        get_key_stats()
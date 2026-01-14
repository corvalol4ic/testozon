import asyncio
import sys
from database.db import database


async def make_admin(user_id: int):
    """Назначение пользователя администратором"""
    # Сначала проверим, существует ли пользователь
    user = await database.get_user(user_id=user_id)

    if not user:
        print(f"❌ Пользователь с ID {user_id} не найден!")
        print("   Сначала пользователь должен зарегистрироваться через /start")
        return False

    # Обновляем статус админа
    from threading import Lock
    import sqlite3

    def sync_make_admin():
        with Lock():
            conn = sqlite3.connect("data/database.db")
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET is_admin = 1 WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return affected > 0

    success = await asyncio.to_thread(sync_make_admin)

    if success:
        print(f"✅ Пользователь {user['full_name']} (ID: {user_id}) назначен администратором!")
        return True
    else:
        print(f"❌ Не удалось назначить администратором пользователя {user_id}")
        return False


async def list_admins():
    """Показать список администраторов"""

    def sync_get_admins():
        import sqlite3
        from threading import Lock

        with Lock():
            conn = sqlite3.connect("data/database.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.* 
                FROM users u
                WHERE u.is_admin = 1 
                ORDER BY u.created_at DESC
            ''')
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]

    admins = await asyncio.to_thread(sync_get_admins)

    if not admins:
        print("👑 Администраторов нет")
        return

    print("👑 Список администраторов:")
    print("=" * 50)

    for admin in admins:
        status = "✅" if admin.get('is_active') else "❌"
        print(f"{status} {admin['user_id']}: {admin['full_name']} (@{admin.get('username', 'нет')})")
        print(f"   📅 Зарегистрирован: {admin['created_at'][:10]}")
        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Утилита управления администраторами")
    parser.add_argument("action", choices=["add", "list", "remove"],
                        help="Действие: add - добавить админа, list - список админов, remove - удалить админа")
    parser.add_argument("--user_id", type=int, help="ID пользователя Telegram")

    args = parser.parse_args()

    if args.action == "add":
        if not args.user_id:
            print("❌ Не указан user_id!")
            print("   Используйте: python make_admin.py add --user_id <ваш_айди>")
            sys.exit(1)

        asyncio.run(make_admin(args.user_id))

    elif args.action == "list":
        asyncio.run(list_admins())

    elif args.action == "remove":
        if not args.user_id:
            print("❌ Не указан user_id!")
            print("   Используйте: python make_admin.py remove --user_id <айди>")
            sys.exit(1)


        # Удаление админ прав
        async def remove_admin():
            from threading import Lock
            import sqlite3

            def sync_remove_admin():
                with Lock():
                    conn = sqlite3.connect("data/database.db")
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE users SET is_admin = 0 WHERE user_id = ?",
                        (args.user_id,)
                    )
                    conn.commit()
                    affected = cursor.rowcount
                    conn.close()
                    return affected > 0

            success = await asyncio.to_thread(sync_remove_admin)

            if success:
                print(f"✅ Админ права у пользователя {args.user_id} удалены!")
            else:
                print(f"❌ Не удалось удалить админ права у пользователя {args.user_id}")


        asyncio.run(remove_admin())
from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from datetime import datetime

from database.db import database

router = Router()


@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user = await database.get_user(user_id=message.from_user.id)

    if user:
        created_at = datetime.fromisoformat(user['created_at'])
        formatted_date = created_at.strftime("%d.%m.%Y %H:%M")

        is_admin = "✅" if user.get('is_admin') else "❌"
        is_active = "✅" if user.get('is_active') else "❌"

        await message.answer(
            f"👤 Ваш профиль:\n\n"
            f"🆔 Telegram ID: {user['user_id']}\n"
            f"👤 Username: @{user['username'] or 'не указан'}\n"
            f"📛 Полное имя: {user['full_name']}\n"
            f"🔑 Ключ доступа: {user['access_key'][:8]}...\n"
            f"💎 План подписки: {user.get('plan_name', 'FREE')}\n"
            f"👑 Админ: {is_admin}\n"
            f"✅ Активен: {is_active}\n"
            f"📅 Регистрация: {formatted_date}"
        )
    else:
        await message.answer("Профиль не найден! Используйте /start для регистрации.")


@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    users_count = await database.get_users_count()
    system_stats = await database.get_system_stats()

    stats_text = (
        f"📊 Статистика бота:\n\n"
        f"👥 Всего пользователей: {users_count}\n"
        f"✅ Активных: {system_stats.get('active_users', 0)}\n"
        f"📈 Всего запросов: {system_stats.get('total_requests', 0)}\n\n"
        f"💎 Распределение по планам:\n"
    )

    for plan_name, count in system_stats.get('users_by_plan', {}).items():
        stats_text += f"• {plan_name}: {count}\n"

    await message.answer(stats_text)


@router.message(Command("admin"))
async def cmd_admin(message: types.Message, command: CommandObject):
    """Админ-команды"""
    user = await database.get_user(user_id=message.from_user.id)

    if not user or not user.get('is_admin'):
        await message.answer("❌ У вас нет прав администратора!")
        return

    args = command.args

    if not args:
        admin_help = (
            "👑 Админ-команды:\n\n"
            "/admin users [число] - Список пользователей\n"
            "/admin search <запрос> - Поиск пользователей\n"
            "/admin plans - Управление планами\n"
            "/admin reset <user_id> - Сброс запросов\n"
            "/admin upgrade <user_id> <plan> - Обновить подписку\n"
            "/admin key <user_id> - Получить ключ пользователя\n"
            "/admin toggle <user_id> - Блокировка/разблокировка\n"
            "/admin make_admin <user_id> - Сделать админом\n"
            "/admin admins - Список админов\n"
            "/admin system - Системная статистика\n"
            "/admin cleanup - Очистка просроченных подписок\n"
        )
        await message.answer(admin_help)

    elif args.startswith("users"):
        try:
            limit = int(args.split()[1]) if len(args.split()) > 1 else 10
        except ValueError:
            limit = 10

        users = await database.get_all_users(limit=limit)

        if not users:
            await message.answer("📭 Пользователей нет")
            return

        users_text = f"👥 Последние {len(users)} пользователей:\n\n"

        for u in users:
            status = "✅" if u.get('is_active') else "❌"
            admin = "👑" if u.get('is_admin') else ""
            users_text += f"{status}{admin} {u['user_id']}: {u['full_name']} ({u.get('plan_name', 'FREE')})\n"

        total_users = await database.get_users_count()
        users_text += f"\n📊 Всего пользователей: {total_users}"

        await message.answer(users_text)

    elif args.startswith("search"):
        try:
            search_query = args.split(maxsplit=1)[1]
            users = await database.search_users(search_query, limit=10)

            if not users:
                await message.answer(f"🔍 По запросу '{search_query}' ничего не найдено")
                return

            users_text = f"🔍 Результаты поиска '{search_query}':\n\n"

            for u in users:
                status = "✅" if u.get('is_active') else "❌"
                users_text += f"{status} {u['user_id']}: {u['full_name']} (@{u.get('username', 'нет')}) - {u.get('plan_name', 'FREE')})\n"

            await message.answer(users_text)

        except IndexError:
            await message.answer("❌ Используйте: /admin search <запрос>")

    elif args.startswith("reset"):
        try:
            user_id = int(args.split()[1])
            await database.reset_user_requests(user_id)
            await message.answer(f"✅ Запросы пользователя {user_id} сброшены!")
        except (IndexError, ValueError):
            await message.answer("❌ Используйте: /admin reset <user_id>")

    elif args.startswith("upgrade"):
        try:
            parts = args.split()
            if len(parts) < 3:
                await message.answer("❌ Используйте: /admin upgrade <user_id> <plan_name>")
                return

            user_id = int(parts[1])
            plan_name = parts[2].upper()

            success = await database.update_user_subscription(user_id, plan_name)

            if success:
                await message.answer(f"✅ Пользователь {user_id} переведен на план {plan_name}!")
            else:
                await message.answer(f"❌ Не удалось обновить подписку. Проверьте ID пользователя и название плана.")

        except (IndexError, ValueError):
            await message.answer("❌ Используйте: /admin upgrade <user_id> <plan_name>")

    elif args.startswith("key"):
        try:
            user_id = int(args.split()[1])
            user = await database.get_user(user_id=user_id)

            if user and user.get('access_key'):
                await message.answer(
                    f"🔑 Ключ доступа пользователя {user_id}:\n\n"
                    f"<code>{user['access_key']}</code>\n\n"
                    f"👤 Имя: {user['full_name']}\n"
                    f"💎 План: {user.get('plan_name', 'FREE')}",
                    parse_mode="HTML"
                )
            else:
                await message.answer(f"❌ Пользователь {user_id} не найден или у него нет ключа")

        except (IndexError, ValueError):
            await message.answer("❌ Используйте: /admin key <user_id>")

    elif args.startswith("toggle"):
        try:
            user_id = int(args.split()[1])
            success = await database.toggle_user_active(user_id)

            if success:
                await message.answer(f"✅ Статус активности пользователя {user_id} изменен!")
            else:
                await message.answer(f"❌ Пользователь {user_id} не найден")

        except (IndexError, ValueError):
            await message.answer("❌ Используйте: /admin toggle <user_id>")

    elif args.startswith("make_admin"):
        try:
            user_id = int(args.split()[1])
            success = await database.make_admin(user_id)

            if success:
                await message.answer(f"✅ Пользователь {user_id} назначен администратором!")
            else:
                await message.answer(f"❌ Пользователь {user_id} не найден")

        except (IndexError, ValueError):
            await message.answer("❌ Используйте: /admin make_admin <user_id>")

    elif args == "admins":
        admins = await database.get_admins()

        if not admins:
            await message.answer("👑 Администраторов нет")
            return

        admins_text = "👑 Список администраторов:\n\n"

        for admin in admins:
            status = "✅" if admin.get('is_active') else "❌"
            admins_text += f"{status} {admin['user_id']}: {admin['full_name']} (@{admin.get('username', 'нет')})\n"

        await message.answer(admins_text)

    elif args == "system":
        stats = await database.get_system_stats()

        stats_text = "🖥️ Системная статистика:\n\n"
        stats_text += f"👥 Всего пользователей: {stats.get('total_users', 0)}\n"
        stats_text += f"✅ Активных: {stats.get('active_users', 0)}\n"
        stats_text += f"📊 Всего запросов: {stats.get('total_requests', 0)}\n\n"

        stats_text += "💎 Пользователи по планам:\n"
        for plan_name, count in stats.get('users_by_plan', {}).items():
            stats_text += f"• {plan_name}: {count}\n"

        stats_text += "\n📈 Запросы за 7 дней:\n"
        for day in stats.get('requests_7d', []):
            date_obj = datetime.fromisoformat(day['date'])
            formatted_date = date_obj.strftime("%d.%m")
            stats_text += f"• {formatted_date}: {day['count']} запр.\n"

        await message.answer(stats_text)

    elif args == "cleanup":
        count = await database.cleanup_expired_subscriptions()
        await message.answer(f"🧹 Очистка завершена. Переведено на FREE план: {count} пользователей")


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
    📚 Основные команды:

    /start - Регистрация и получение ключа
    /profile - Ваш профиль
    /key - Получить ключ доступа
    /regenerate_key - Сгенерировать новый ключ
    /subscription - Информация о подписке
    /plans - Доступные планы
    /upgrade - Улучшить подписку
    /access_check - Проверка доступа
    /stats - Статистика бота
    /help - Помощь

    💡 Особенности:
    • Уникальный ключ доступа для API
    • Планы подписки с разными лимитами
    • Отслеживание использованных запросов
    • Автоматическая проверка доступа

    🔑 Ключ доступа нужен для:
    • Интеграции с другими сервисами
    • Автоматических запросов к боту
    • Использования API функционала
    """
    await message.answer(help_text)


@router.message(Command("my_requests"))
async def cmd_my_requests(message: types.Message):
    """Просмотр последних запросов"""
    requests = await database.get_user_requests(message.from_user.id, limit=10)

    if not requests:
        await message.answer("📭 У вас пока нет запросов")
        return

    requests_text = "📝 Ваши последние запросы:\n\n"

    for i, req in enumerate(requests, 1):
        date_obj = datetime.fromisoformat(req['created_at'])
        formatted_date = date_obj.strftime("%H:%M %d.%m")
        request_type = req.get('request_type', 'unknown')

        # Обрезаем длинный текст
        request_data = req.get('request_data', '')[:30]
        if len(req.get('request_data', '')) > 30:
            request_data += "..."

        requests_text += f"{i}. {formatted_date} [{request_type}]: {request_data}\n"

    await message.answer(requests_text)
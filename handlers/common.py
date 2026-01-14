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

        profile_text = (
            f"👤 Ваш профиль:\n\n"
            f"🆔 Telegram ID: {user['user_id']}\n"
            f"👤 Username: @{user['username'] or 'не указан'}\n"
            f"📛 Полное имя: {user['full_name']}\n"
            f"💎 План подписки: {user.get('plan_name', 'FREE')}\n"
            f"👑 Админ: {is_admin}\n"
            f"✅ Активен: {is_active}\n"
            f"📅 Регистрация: {formatted_date}"
        )

        # Добавляем информацию о ключе, если он есть
        activation_key = user.get('activation_key')
        if activation_key:
            profile_text += f"\n🔑 Ключ активации: <code>{activation_key}</code>"

        await message.answer(profile_text, parse_mode="HTML")
    else:
        await message.answer("Профиль не найден! Используйте /start для регистрации.")


@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Статистика бота"""
    try:
        system_stats = await database.get_system_stats()
        users_count = system_stats.get('total_users', 0)
        active_users = system_stats.get('active_users', 0)
        users_with_keys = system_stats.get('users_with_keys', 0)
        total_keys = system_stats.get('total_keys', 0)
        used_keys = system_stats.get('used_keys', 0)

        stats_text = (
            f"📊 Статистика бота:\n\n"
            f"👥 Всего пользователей: {users_count}\n"
            f"✅ Активных: {active_users}\n"
            f"🔑 Пользователей с ключами: {users_with_keys}\n"
            f"🗝️ Всего ключей: {total_keys}\n"
            f"✅ Использовано ключей: {used_keys}\n"
            f"🆕 Доступно ключей: {total_keys - used_keys}"
        )

        await message.answer(stats_text)
    except Exception as e:
        # Если метод не существует, используем простую статистику
        users_count = await database.get_users_count()
        users = await database.get_all_users(limit=10)

        active_users = 0
        users_with_keys = 0

        for user in users:
            if user.get('is_active'):
                active_users += 1
            if user.get('activation_key'):
                users_with_keys += 1

        stats_text = (
            f"📊 Статистика бота:\n\n"
            f"👥 Всего пользователей: {users_count}\n"
            f"✅ Активных: {active_users}\n"
            f"🔑 Пользователей с ключами: {users_with_keys}"
        )

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
            plan = u.get('plan_name', 'FREE')
            users_text += f"{status}{admin} {u['user_id']}: {u['full_name']} ({plan})\n"

        total_users = await database.get_users_count()
        users_text += f"\n📊 Всего пользователей: {total_users}"

        await message.answer(users_text)

    elif args.startswith("search"):
        try:
            search_query = args.split(maxsplit=1)[1]

            # Простой поиск по всем пользователям
            users = await database.get_all_users(limit=100)
            found_users = []

            for u in users:
                if (search_query.lower() in u['full_name'].lower() or
                        (u['username'] and search_query.lower() in u['username'].lower()) or
                        search_query in str(u['user_id'])):
                    found_users.append(u)

            if not found_users:
                await message.answer(f"🔍 По запросу '{search_query}' ничего не найдено")
                return

            users_text = f"🔍 Результаты поиска '{search_query}':\n\n"

            for u in found_users[:10]:
                status = "✅" if u.get('is_active') else "❌"
                users_text += f"{status} {u['user_id']}: {u['full_name']} (@{u.get('username', 'нет')}) - {u.get('plan_name', 'FREE')}\n"

            if len(found_users) > 10:
                users_text += f"\n... и еще {len(found_users) - 10} пользователей"

            await message.answer(users_text)

        except IndexError:
            await message.answer("❌ Используйте: /admin search <запрос>")


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
    📚 Основные команды:

    /start - Регистрация и начало работы
    /profile - Ваш профиль
    /subscription - Информация о подписке
    /plans - Доступные планы
    /activate - Активировать ключ
    /my_key - Показать ваш ключ
    /key_status - Статус ключа
    /deactivate - Отвязать ключ
    /links - Управление ссылками
    /stats - Статистика бота
    /help - Помощь

    🔗 Управление ссылками:
    /links - Меню ссылок
    /my_links - Просмотр ссылок
    /link <id> - Действия с ссылкой

    💎 Особенности:
    • Уникальные ключи активации для каждого пользователя
    • Планы подписки с разными лимитами
    • Каждый ключ можно использовать только один раз
    • Защита от повторной активации

    🔒 Безопасность:
    • Ключи привязываются к аккаунту Telegram
    • Невозможно использовать один ключ на нескольких аккаунтах
    • После отвязки ключ становится неактивным
    """
    await message.answer(help_text)


@router.message(Command("my_requests"))
async def cmd_my_requests(message: types.Message):
    """Просмотр последних запросов (заглушка)"""
    await message.answer(
        "📝 История запросов\n\n"
        "Эта функция находится в разработке.\n"
        "Скоро вы сможете просматривать историю своих запросов."
    )
from aiogram import Router, types
from aiogram.filters import Command
from datetime import datetime

router = Router()


@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user = await database.get_user(message.from_user.id)

    if user:
        created_at = datetime.fromisoformat(user['created_at'])
        formatted_date = created_at.strftime("%d.%m.%Y %H:%M")

        await message.answer(
            f"👤 Ваш профиль:\n\n"
            f"🆔 ID: {user['user_id']}\n"
            f"👤 Username: @{user['username'] or 'не указан'}\n"
            f"📛 Имя: {user['full_name']}\n"
            f"📅 Зарегистрирован: {formatted_date}\n"
            f"🔢 Внутренний ID: {user['id']}"
        )
    else:
        await message.answer("Профиль не найден! Используйте /start для регистрации.")


@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    users_count = await database.get_user_count()
    users = await database.get_all_users()

    if users:
        last_user = users[0]
        last_registered = datetime.fromisoformat(last_user['created_at']).strftime("%d.%m.%Y")

        stats_text = (
            f"📊 Статистика бота:\n\n"
            f"👥 Всего пользователей: {users_count}\n"
            f"🆕 Последний регистрация: {last_registered}\n"
            f"👤 Последний пользователь: {last_user['full_name']}"
        )
    else:
        stats_text = "📊 В базе данных пока нет пользователей"

    await message.answer(stats_text)


@router.message(Command("my_messages"))
async def cmd_my_messages(message: types.Message):
    messages = await database.get_user_messages(message.from_user.id, limit=5)

    if messages:
        text = "📝 Ваши последние сообщения:\n\n"
        for msg in messages:
            date = datetime.fromisoformat(msg['created_at']).strftime("%H:%M %d.%m")
            text += f"• {date}: {msg['text'][:50]}...\n"
    else:
        text = "📝 У вас пока нет сохраненных сообщений"

    await message.answer(text)


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
    📚 Доступные команды:

    /start - Начать работу с ботом
    /help - Получить помощь
    /profile - Посмотреть профиль
    /stats - Статистика бота
    /my_messages - Мои последние сообщения

    ✨ Возможности:
    - Работа с SQLite базой данных
    - Сохранение пользователей и сообщений
    - Инлайн и reply клавиатуры
    - Полная асинхронность

    💾 Все ваши данные сохраняются локально
    """
    await message.answer(help_text)
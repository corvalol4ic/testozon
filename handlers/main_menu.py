from aiogram import Router, types, F
from aiogram.filters import Command
from keyboards.reply import get_links_menu_keyboard, get_main_menu
from database.db import database

router = Router()


@router.message(F.text == "🔑 Активация ключа")
async def activation_menu(message: types.Message):
    """Меню активации ключа"""
    await message.answer(
        "🔑 Активация ключа\n\n"
        "Используйте команду /activate для активации ключа.\n"
        "Или /check_key для проверки ключа без активации.",
        reply_markup=get_main_menu()
    )


@router.message(F.text == "🔗 Управление ссылками")
async def links_menu(message: types.Message):
    """Переход в меню ссылок"""
    # Проверяем доступ
    access_check = await database.check_user_access(message.from_user.id)

    if not access_check['has_access']:
        await message.answer(
            "❌ Для доступа к управлению ссылками нужен активный ключ.\n"
            "Используйте /activate для активации."
        )
        return

    await message.answer(
        "🔗 Управление ссылками\n\n"
        "Выберите действие:",
        reply_markup=get_links_menu_keyboard()
    )


@router.message(F.text == "📊 Моя статистика")
async def my_stats_menu(message: types.Message):
    """Статистика пользователя"""
    from handlers.start import cmd_subscription
    await cmd_subscription(message)


@router.message(F.text == "ℹ️ Помощь")
async def help_menu(message: types.Message):
    """Помощь"""
    from handlers.common import cmd_help
    await cmd_help(message)


@router.message(Command("menu"))
async def cmd_menu(message: types.Message):
    """Команда для показа главного меню"""
    await message.answer(
        "🏠 Главное меню\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu()
    )


@router.message(F.text == "⬅️ Назад")
async def back_button(message: types.Message):
    """Обработка кнопки Назад"""
    await cmd_menu(message)
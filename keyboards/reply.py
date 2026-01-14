from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню бота"""
    builder = ReplyKeyboardBuilder()

    builder.add(KeyboardButton(text="🔑 Активация ключа"))
    builder.add(KeyboardButton(text="🔗 Управление ссылками"))
    builder.add(KeyboardButton(text="📊 Моя статистика"))
    builder.add(KeyboardButton(text="ℹ️ Помощь"))

    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)


def get_links_menu_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура меню ссылок"""
    builder = ReplyKeyboardBuilder()

    builder.add(KeyboardButton(text="📥 Добавить ссылку"))
    builder.add(KeyboardButton(text="📋 Мои ссылки"))
    builder.add(KeyboardButton(text="🔍 Поиск ссылок"))
    builder.add(KeyboardButton(text="📊 Статистика ссылок"))
    builder.add(KeyboardButton(text="📤 Экспорт ссылок"))
    builder.add(KeyboardButton(text="🏠 Главное меню"))

    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)


def get_categories_keyboard(categories: list) -> ReplyKeyboardMarkup:
    """Клавиатура с категориями"""
    builder = ReplyKeyboardBuilder()

    for category in categories[:8]:  # Ограничиваем 8 кнопками
        builder.add(KeyboardButton(text=category))

    builder.add(KeyboardButton(text="/skip"))
    builder.add(KeyboardButton(text="/cancel"))

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_contact_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для запроса контакта"""
    keyboard = [
        [KeyboardButton(text="📱 Отправить контакт", request_contact=True)]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Простая клавиатура с кнопкой Назад"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="⬅️ Назад"))
    return builder.as_markup(resize_keyboard=True)
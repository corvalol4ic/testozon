from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📊 Статистика"))
    builder.add(KeyboardButton(text="ℹ️ Помощь"))
    builder.add(KeyboardButton(text="👤 Профиль"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_contact_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="📱 Отправить контакт", request_contact=True)]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
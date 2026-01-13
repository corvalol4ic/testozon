from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_start_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="📚 Документация",
        url="https://docs.aiogram.dev/"
    ))
    builder.add(InlineKeyboardButton(
        text="⭐ GitHub",
        url="https://github.com/aiogram/aiogram"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ Удалить сообщение",
        callback_data="delete_message"
    ))
    builder.adjust(2)
    return builder.as_markup()
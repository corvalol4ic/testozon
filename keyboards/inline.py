from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_activation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для активации"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🔑 Активировать ключ",
        callback_data="activate_key"
    ))
    builder.add(InlineKeyboardButton(
        text="💎 Купить подписку",
        url="https://your-site.com/buy"  # Замените на свою ссылку
    ))
    builder.add(InlineKeyboardButton(
        text="📋 Моя подписка",
        callback_data="my_subscription"
    ))
    builder.adjust(2)
    return builder.as_markup()

def get_admin_keys_keyboard() -> InlineKeyboardMarkup:
    """Админ клавиатура для управления ключами"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🔄 Сгенерировать ключи",
        callback_data="admin_generate_keys"
    ))
    builder.add(InlineKeyboardButton(
        text="📋 Список ключей",
        callback_data="admin_list_keys"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 Статистика",
        callback_data="admin_keys_stats"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ Отозвать ключ",
        callback_data="admin_revoke_key"
    ))
    builder.adjust(2)
    return builder.as_markup()
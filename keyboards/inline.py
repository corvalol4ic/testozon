from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_start_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🔑 Получить ключ",
        callback_data="get_access_key"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 Моя подписка",
        callback_data="my_subscription"
    ))
    builder.add(InlineKeyboardButton(
        text="💎 Планы",
        callback_data="view_plans"
    ))
    builder.add(InlineKeyboardButton(
        text="🔄 Обновить ключ",
        callback_data="regenerate_key"
    ))
    builder.adjust(2)
    return builder.as_markup()


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="💎 Улучшить подписку",
        callback_data="upgrade_subscription"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 Статистика",
        callback_data="view_stats"
    ))
    builder.add(InlineKeyboardButton(
        text="🔑 Ключ доступа",
        callback_data="get_access_key"
    ))
    builder.adjust(2)
    return builder.as_markup()


def get_upgrade_keyboard(plans: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for plan in plans:
        builder.add(InlineKeyboardButton(
            text=f"💎 {plan}",
            callback_data=f"upgrade_to_{plan.lower()}"
        ))

    builder.add(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="cancel_upgrade"
    ))

    builder.adjust(1)
    return builder.as_markup()
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
        text="🔍 Проверить ключ",
        callback_data="check_key"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 Статус ключа",
        callback_data="key_status"
    ))
    builder.add(InlineKeyboardButton(
        text="🔄 Заменить ключ",
        callback_data="replace_key"
    ))
    builder.adjust(2, 2)
    return builder.as_markup()


def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения действий"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="✅ Да, подтверждаю",
        callback_data=f"confirm_{action}"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ Нет, отмена",
        callback_data=f"cancel_{action}"
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
    builder.adjust(2, 1)
    return builder.as_markup()


def get_link_actions_keyboard(link_id: int) -> InlineKeyboardMarkup:
    """Inline клавиатура для действий со ссылкой"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="✏️ Редактировать",
        callback_data=f"edit_link_{link_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="🗑️ Удалить",
        callback_data=f"delete_link_{link_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="📋 Все ссылки",
        callback_data="show_all_links"
    ))

    builder.adjust(2, 1)
    return builder.as_markup()


def get_upgrade_keyboard(plans: list) -> InlineKeyboardMarkup:
    """Клавиатура для обновления подписки"""
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
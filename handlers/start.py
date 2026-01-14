from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from database.db import database
from keyboards.inline import get_activation_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    # Добавляем пользователя в БД
    user_data = await database.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    if user_data:
        # Проверяем, есть ли активный ключ
        key_data = await database.get_user_active_key(message.from_user.id)

        welcome_text = f"👋 Привет, {message.from_user.full_name}!\n\n"

        if key_data:
            welcome_text += (
                f"✅ У вас активирован ключ доступа!\n"
                f"💎 План: {key_data['plan_name']}\n"
                f"🔑 Ключ: {key_data['key_code']}\n\n"
                f"📊 Используйте /subscription для деталей подписки"
            )
        else:
            welcome_text += (
                f"🔐 Для доступа к премиум функциям нужен ключ активации.\n\n"
                f"💎 Как получить ключ:\n"
                f"1. Купите подписку на нашем сайте\n"
                f"2. Получите уникальный ключ\n"
                f"3. Активируйте его командой /activate\n\n"
                f"📞 Связь с администратором: @admin"
            )

        await message.answer(
            welcome_text,
            reply_markup=get_activation_keyboard()
        )
    else:
        await message.answer(
            "Произошла ошибка при регистрации. Попробуйте еще раз."
        )


@router.message(Command("subscription"))
async def cmd_subscription(message: types.Message):
    """Информация о подписке с ключом"""
    user_stats = await database.get_user_stats(message.from_user.id)

    if not user_stats:
        await message.answer("❌ Сначала зарегистрируйтесь через /start")
        return

    activation_key = user_stats.get('activation_key')

    subscription_text = (
        f"📊 Ваша подписка:\n\n"
        f"• План: <b>{user_stats.get('plan_name', 'FREE')}</b>\n"
        f"• Описание: {user_stats.get('plan_description', 'Бесплатный план')}\n"
        f"• Цена: {user_stats.get('plan_price', 0)} USD/мес\n\n"
        f"📈 Использование:\n"
        f"• Запросы: {user_stats.get('requests_used', 0)}/{user_stats.get('requests_limit', 100)}\n"
        f"• Осталось: {user_stats.get('requests_remaining', 100)} запросов\n"
        f"• Лимит плана: {user_stats.get('plan_max_requests', 100)} запр./мес\n\n"
        f"📅 Статус:\n"
        f"• Начало: {user_stats.get('subscription_start', 'N/A')}\n"
        f"• Окончание: {user_stats.get('subscription_end', 'N/A')}\n"
        f"• Осталось дней: {int(user_stats.get('days_remaining', 0)) if user_stats.get('days_remaining') else 0}\n"
    )

    if activation_key:
        subscription_text += f"\n🔑 Ключ активации: <code>{activation_key}</code>"

    await message.answer(
        subscription_text,
        parse_mode="HTML",
        reply_markup=get_activation_keyboard()
    )
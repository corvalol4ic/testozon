from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from database.db import database
from keyboards.inline import get_activation_keyboard
from keyboards.reply import get_links_menu_keyboard

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
                f"📊 Используйте /subscription для деталей подписки\n"
                f"🔗 Для управления ссылками используйте /links"
            )
            # Показываем меню ссылок если есть ключ
            await message.answer(
                welcome_text,
                reply_markup=get_links_menu_keyboard()
            )
        else:
            welcome_text += (
                f"🔐 Для доступа к премиум функциям нужен ключ активации.\n\n"
                f"💎 Как получить ключ:\n"
                f"1. Купите подписку на нашем сайте\n"
                f"2. Получите уникальный ключ (формат: XXXX-XXXX-XXXX-XXXX)\n"
                f"3. Активируйте его командой /activate\n\n"
                f"🔒 Важно: каждый ключ можно активировать только один раз "
                f"и только на одном аккаунте.\n\n"
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
        subscription_text += f"\n\n⚠️ Этот ключ привязан только к вашему аккаунту."

    await message.answer(
        subscription_text,
        parse_mode="HTML",
        reply_markup=get_activation_keyboard()
    )


@router.message(Command("plans"))
async def cmd_plans(message: types.Message):
    """Просмотр доступных планов"""
    plans = await database.get_all_subscription_plans()

    if not plans:
        await message.answer("Планы подписки не найдены.")
        return

    plans_text = "💎 Доступные планы подписки:\n\n"

    for plan in plans:
        plans_text += (
            f"• <b>{plan['name']}</b>\n"
            f"  {plan['description']}\n"
            f"  💰 Цена: {plan['price']} USD/мес\n"
            f"  📊 Лимит: {plan['max_requests']} запросов\n"
            f"  📅 Длительность: {plan['duration_days']} дней\n\n"
        )

    await message.answer(plans_text, parse_mode="HTML")


@router.message(Command("upgrade"))
async def cmd_upgrade(message: types.Message, state: FSMContext):
    """Обновление подписки"""
    plans = await database.get_all_subscription_plans()

    if len(plans) > 1:
        from keyboards.inline import get_upgrade_keyboard
        await message.answer(
            "Выберите план для обновления:",
            reply_markup=get_upgrade_keyboard([p['name'] for p in plans if p['name'] != 'FREE'])
        )
    else:
        await message.answer("Нет доступных планов для обновления.")


@router.message(Command("access_check"))
async def cmd_access_check(message: types.Message):
    """Проверка доступа"""
    access = await database.check_user_access(message.from_user.id)

    if access['has_access']:
        status = "✅ Доступ разрешен"
    else:
        status = "❌ Доступ запрещен"

    check_text = (
        f"{status}\n\n"
        f"📊 Детали:\n"
        f"• Активен: {'✅' if access['is_active'] else '❌'}\n"
        f"• Подписка активна: {'✅' if access['is_subscription_active'] else '❌'}\n"
        f"• Есть запросы: {'✅' if access['has_requests'] else '❌'}\n"
        f"• Использовано: {access['requests_used']}/{access['requests_limit']}\n"
        f"• План: {access['plan_name']}\n"
        f"• Причина: {access['reason']}"
    )

    await message.answer(check_text)


@router.callback_query(F.data == "delete_message")
async def delete_message(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer("Сообщение удалено!")
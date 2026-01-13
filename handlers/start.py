from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from database.db import database
from keyboards.inline import get_start_keyboard, get_subscription_keyboard
from keyboards.reply import get_main_menu

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
        access_key = user_data['access_key']

        await message.answer(
            f"👋 Привет, {message.from_user.full_name}!\n\n"
            f"✅ Вы успешно зарегистрированы!\n\n"
            f"🔑 Ваш ключ доступа:\n"
            f"<code>{access_key}</code>\n\n"
            f"💡 Сохраните этот ключ в безопасном месте!\n"
            f"Он нужен для API-доступа к боту.",
            parse_mode="HTML",
            reply_markup=get_start_keyboard()
        )

        # Показываем информацию о подписке
        stats = await database.get_user_stats(message.from_user.id)

        subscription_info = (
            f"📊 Ваша текущая подписка:\n"
            f"• План: {stats.get('plan_name', 'FREE')}\n"
            f"• Использовано запросов: {stats.get('requests_used', 0)}/{stats.get('requests_limit', 100)}\n"
            f"• Доступно: {stats.get('requests_remaining', 100)} запросов\n"
            f"• Подписка активна до: {stats.get('subscription_end', 'N/A')}"
        )

        await message.answer(
            subscription_info,
            reply_markup=get_subscription_keyboard()
        )
    else:
        await message.answer(
            "Вы уже зарегистрированы!",
            reply_markup=get_main_menu()
        )


@router.message(Command("key"))
async def cmd_get_key(message: types.Message):
    """Получить ключ доступа"""
    user = await database.get_user(user_id=message.from_user.id)

    if user and user.get('access_key'):
        await message.answer(
            f"🔑 Ваш ключ доступа:\n\n"
            f"<code>{user['access_key']}</code>\n\n"
            f"⚠️ Никому не передавайте этот ключ!",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "Ключ доступа не найден. Используйте /start для регистрации."
        )


@router.message(Command("regenerate_key"))
async def cmd_regenerate_key(message: types.Message):
    """Сгенерировать новый ключ доступа"""
    new_key = await database.regenerate_access_key(message.from_user.id)

    if new_key:
        await message.answer(
            f"✅ Ключ успешно обновлен!\n\n"
            f"🔑 Новый ключ доступа:\n"
            f"<code>{new_key}</code>\n\n"
            f"⚠️ Старый ключ больше недействителен!",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Ошибка при генерации ключа. Попробуйте позже."
        )


@router.message(Command("subscription"))
async def cmd_subscription(message: types.Message):
    """Информация о подписке"""
    stats = await database.get_user_stats(message.from_user.id)

    if not stats:
        await message.answer("Информация о подписке не найдена.")
        return

    days_remaining = int(stats.get('days_remaining', 0)) if stats.get('days_remaining') else 0

    subscription_text = (
        f"📊 Ваша подписка:\n\n"
        f"• План: <b>{stats.get('plan_name', 'FREE')}</b>\n"
        f"• Описание: {stats.get('plan_description', 'Бесплатный план')}\n"
        f"• Цена: {stats.get('plan_price', 0)} USD/мес\n\n"
        f"📈 Использование:\n"
        f"• Запросы: {stats.get('requests_used', 0)}/{stats.get('requests_limit', 100)}\n"
        f"• Осталось: {stats.get('requests_remaining', 100)} запросов\n"
        f"• Лимит плана: {stats.get('plan_max_requests', 100)} запр./мес\n\n"
        f"📅 Статус:\n"
        f"• Начало: {stats.get('subscription_start', 'N/A')}\n"
        f"• Окончание: {stats.get('subscription_end', 'N/A')}\n"
        f"• Осталось дней: {days_remaining if days_remaining > 0 else 0}\n\n"
        f"💎 Использовано за 30 дней:\n"
        f"• Запросов: {stats.get('requests_30d', {}).get('total_requests_30d', 0)}\n"
        f"• Токенов: {stats.get('requests_30d', {}).get('total_tokens_30d', 0)}"
    )

    await message.answer(
        subscription_text,
        parse_mode="HTML",
        reply_markup=get_subscription_keyboard()
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
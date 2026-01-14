from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from database.db import database
from keyboards.inline import get_activation_keyboard, get_admin_keys_keyboard, get_confirmation_keyboard
from keyboards.reply import get_links_menu_keyboard

router = Router()


class ActivationStates(StatesGroup):
    waiting_for_key = State()


@router.message(Command("activate"))
async def cmd_activate(message: types.Message, state: FSMContext):
    """Команда для активации ключа"""
    await message.answer(
        "🔑 Введите ваш ключ активации:\n\n"
        "Формат: XXXX-XXXX-XXXX-XXXX\n"
        "Пример: ABCD-EFGH-IJKL-MNOP\n\n"
        "❌ Для отмены введите /cancel"
    )
    await state.set_state(ActivationStates.waiting_for_key)


@router.message(ActivationStates.waiting_for_key)
async def process_activation_key(message: types.Message, state: FSMContext):
    """Обработка введенного ключа"""
    key_code = message.text.strip().upper()

    # Отмена
    if message.text.lower() == '/cancel':
        await state.clear()
        await message.answer("❌ Активация отменена")
        return

    # Проверяем формат ключа (XXXX-XXXX-XXXX-XXXX)
    if len(key_code) != 19 or key_code.count('-') != 3:
        await message.answer(
            "❌ Неверный формат ключа!\n\n"
            "Правильный формат: XXXX-XXXX-XXXX-XXXX\n"
            "Пример: ABCD-EFGH-IJKL-MNOP\n\n"
            "Попробуйте еще раз или введите /cancel для отмены"
        )
        return

    # Проверяем, что каждая часть содержит только разрешенные символы
    parts = key_code.split('-')
    if len(parts) != 4:
        await message.answer(
            "❌ Неверный формат ключа! Должно быть 4 группы символов\n\n"
            "Попробуйте еще раз или введите /cancel для отмены"
        )
        return

    for part in parts:
        if len(part) != 4:
            await message.answer(
                f"❌ Неверная длина группы '{part}'! Должно быть 4 символа\n\n"
                "Попробуйте еще раз или введите /cancel для отмены"
            )
            return

    # Проверяем ключ
    validation = await database.validate_key(key_code)

    if not validation['valid']:
        await message.answer(
            f"❌ {validation['error']}\n\n"
            f"Проверьте ключ и попробуйте еще раз или введите /cancel"
        )
        return

    # Активируем ключ
    result = await database.activate_key(message.from_user.id, key_code)

    if result['success']:
        await message.answer(
            f"✅ Ключ успешно активирован!\n\n"
            f"💎 План: <b>{result['plan_name']}</b>\n"
            f"📊 Лимит запросов: {result['max_requests']}/мес\n"
            f"📅 Начало подписки: {result['start_date']}\n"
            f"📅 Окончание: {result['end_date']}\n"
            f"⏳ Длительность: {result['duration_days']} дней\n\n"
            f"🔒 Ключ привязан к вашему аккаунту и не может быть использован повторно.\n\n"
            f"🎉 Теперь у вас есть доступ к премиум функциям!\n\n"
            f"🔗 Для управления ссылками используйте /links",
            parse_mode="HTML"
        )

        # Показываем меню ссылок
        await message.answer(
            "📋 Выберите действие в меню ссылок:",
            reply_markup=get_links_menu_keyboard()
        )

        # Показываем текущую статистику
        user_stats = await database.get_user_stats(message.from_user.id)
        if user_stats:
            await message.answer(
                f"📊 Ваша текущая статистика:\n\n"
                f"• План: {user_stats.get('plan_name', 'FREE')}\n"
                f"• Использовано: {user_stats.get('requests_used', 0)}/{user_stats.get('requests_limit', 100)}\n"
                f"• Осталось запросов: {user_stats.get('requests_remaining', 100)}\n"
                f"• Подписка до: {user_stats.get('subscription_end', 'N/A')}"
            )
    else:
        await message.answer(
            f"❌ {result['error']}\n\n"
            f"Используйте /start для регистрации, затем повторите активацию."
        )

    await state.clear()


@router.message(Command("my_key"))
async def cmd_my_key(message: types.Message):
    """Показать активный ключ пользователя"""
    user = await database.get_user(user_id=message.from_user.id)

    if not user:
        await message.answer("❌ Сначала зарегистрируйтесь через /start")
        return

    activation_key = user.get('activation_key')

    if activation_key:
        key_info = await database.validate_key(activation_key)

        if key_info['valid']:
            key_status = "✅ Активен и привязан к вашему аккаунту"
        else:
            key_status = f"❌ {key_info.get('error', 'Недействителен')}"

        await message.answer(
            f"🔑 Ваш ключ активации:\n\n"
            f"<code>{activation_key}</code>\n\n"
            f"💎 План: {key_info.get('plan_name', 'Неизвестно')}\n"
            f"📊 Лимит: {key_info.get('max_requests', 0)} запросов\n"
            f"📅 Создан: {key_info.get('created_at', 'N/A')[:10]}\n"
            f"📅 Истекает: {key_info.get('expires_at', 'N/A')[:10] if key_info.get('expires_at') else 'Бессрочно'}\n"
            f"📊 Статус: {key_status}\n\n"
            f"⚠️ Этот ключ привязан только к вашему аккаунту и "
            f"не может быть использован повторно.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "🔐 У вас нет активного ключа активации.\n\n"
            "💎 Чтобы получить доступ к премиум функциям:\n"
            "1. Купите подписку на нашем сайте\n"
            "2. Получите ключ активации\n"
            "3. Используйте команду /activate\n\n"
            "📞 Для покупки подписки обратитесь к администратору."
        )


@router.message(Command("check_key"))
async def cmd_check_key(message: types.Message, state: FSMContext):
    """Проверить ключ без активации"""
    await message.answer(
        "🔍 Введите ключ для проверки:\n\n"
        "Я проверю его валидность и покажу информацию о плане.\n\n"
        "Формат: XXXX-XXXX-XXXX-XXXX\n\n"
        "❌ Для отмены введите /cancel"
    )
    await state.set_state(ActivationStates.waiting_for_key)


@router.message(Command("deactivate"))
async def cmd_deactivate(message: types.Message):
    """Отвязка текущего ключа (переход на FREE план)"""
    user = await database.get_user(user_id=message.from_user.id)

    if not user:
        await message.answer("❌ Сначала зарегистрируйтесь через /start")
        return

    if not user.get('activation_key_id'):
        await message.answer("🔓 У вас нет активированного ключа.")
        return

    # Запрашиваем подтверждение
    await message.answer(
        "⚠️ Вы уверены, что хотите отвязать текущий ключ?\n\n"
        "После отвязки:\n"
        "• Вы перейдете на FREE план (50 запросов/мес)\n"
        "• Текущий ключ будет отмечен как использованный\n"
        "• Ключ нельзя будет использовать повторно\n\n"
        "Для подтверждения отвязки нажмите кнопку ниже:",
        reply_markup=get_confirmation_keyboard("deactivate_key")
    )


@router.message(Command("replace_key"))
async def cmd_replace_key(message: types.Message):
    """Замена текущего ключа на новый"""
    user = await database.get_user(user_id=message.from_user.id)

    if not user:
        await message.answer("❌ Сначала зарегистрируйтесь через /start")
        return

    if not user.get('activation_key_id'):
        await message.answer("🔓 У вас нет активированного ключа. Используйте /activate")
        return

    await message.answer(
        "🔄 Замена ключа\n\n"
        "Для замены ключа:\n"
        "1. Сначала отвяжите текущий ключ командой /deactivate\n"
        "2. Затем активируйте новый ключ командой /activate\n\n"
        "⚠️ Внимание: текущий ключ будет отмечен как использованный "
        "и не сможет быть активирован повторно."
    )


@router.message(Command("key_status"))
async def cmd_key_status(message: types.Message):
    """Статус ключа с подробной информацией"""
    user = await database.get_user(user_id=message.from_user.id)

    if not user:
        await message.answer("❌ Сначала зарегистрируйтесь через /start")
        return

    activation_key = user.get('activation_key')

    if activation_key:
        # Получаем детальную информацию о ключе
        key_info = await database.validate_key(activation_key)

        if key_info['valid']:
            status = "✅ Активен и привязан к вашему аккаунту"
            key_details = (
                f"🔑 Ключ: <code>{activation_key}</code>\n"
                f"💎 План: {key_info['plan_name']}\n"
                f"📊 Лимит: {key_info['max_requests']} запросов\n"
                f"📅 Создан: {key_info.get('created_at', 'N/A')[:10]}\n"
                f"📅 Истекает: {key_info.get('expires_at', 'N/A')[:10] if key_info.get('expires_at') else 'Бессрочно'}\n"
                f"📊 Статус: {status}\n\n"
                f"⚠️ Этот ключ привязан только к вашему аккаунту и "
                f"не может быть использован повторно."
            )
        else:
            key_details = (
                f"🔑 Ключ: <code>{activation_key}</code>\n"
                f"❌ Статус: {key_info['error']}\n\n"
                f"ℹ️ {key_info.get('error', 'Ключ недействителен')}"
            )
    else:
        key_details = (
            "🔐 У вас нет активного ключа активации.\n\n"
            "💎 Чтобы получить доступ к премиум функциям:\n"
            "1. Купите подписку на нашем сайте\n"
            "2. Получите ключ активации\n"
            "3. Используйте команду /activate\n\n"
            "⚠️ Каждый ключ можно активировать только один раз "
            "и только на одном аккаунте."
        )

    await message.answer(key_details, parse_mode="HTML")


@router.message(Command("keys_info"))
async def cmd_keys_info(message: types.Message):
    """Информация о ключах и подписках"""
    info_text = """
    🔑 Система ключей активации

    💎 Как это работает:
    1. Вы покупаете подписку на нашем сайте
    2. Получаете уникальный ключ активации
    3. Активируете ключ в боте командой /activate
    4. Получаете доступ к премиум функциям

    🔒 Защита от повторного использования:
    • Каждый ключ можно активировать только один раз
    • Ключ привязывается к конкретному аккаунту Telegram
    • После активации ключ нельзя использовать повторно
    • Ключ нельзя передать другому пользователю

    🔧 Управление ключами:
    /activate - Активировать ключ
    /deactivate - Отвязать текущий ключ
    /key_status - Статус вашего ключа
    /my_key - Показать ваш ключ
    /check_key - Проверить ключ

    ⚠️ Важно:
    • При отвязке ключа вы переходите на FREE план
    • Отвязанный ключ остается использованным
    • Новый ключ нужно покупать отдельно
    """
    await message.answer(info_text)


# ==================== АДМИН КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ КЛЮЧАМИ ====================

@router.message(Command("admin_keys"))
async def cmd_admin_keys(message: types.Message, command: CommandObject):
    """Админ: управление ключами"""
    user = await database.get_user(user_id=message.from_user.id)

    if not user or not user.get('is_admin'):
        await message.answer("❌ У вас нет прав администратора!")
        return

    args = command.args

    if not args:
        help_text = (
            "👑 Админ: Управление ключами\n\n"
            "/admin_keys generate <план> [количество] - Сгенерировать ключи\n"
            "/admin_keys list <план> [used/all] - Список ключей\n"
            "/admin_keys check <ключ> - Проверить ключ\n"
            "/admin_keys stats - Статистика ключей\n"
            "/admin_keys user <user_id> - Ключ пользователя"
        )
        await message.answer(help_text)

    elif args.startswith("generate"):
        try:
            parts = args.split()
            if len(parts) < 2:
                await message.answer("❌ Используйте: /admin_keys generate <план> [количество=1]")
                return

            plan_name = parts[1].upper()
            quantity = int(parts[2]) if len(parts) > 2 else 1

            if quantity > 100:
                await message.answer("❌ Максимум 100 ключей за раз")
                return

            keys = await database.generate_activation_keys(plan_name, quantity)

            if not keys:
                await message.answer(f"❌ Не удалось сгенерировать ключи для плана {plan_name}")
                return

            keys_text = f"✅ Сгенерировано {len(keys)} ключей для плана {plan_name}:\n\n"

            for key in keys:
                keys_text += f"<code>{key}</code>\n"

            keys_text += f"\n📋 Сохраните эти ключи! Они не будут показаны снова."

            await message.answer(keys_text, parse_mode="HTML")

        except (IndexError, ValueError) as e:
            await message.answer(f"❌ Ошибка: {e}\nИспользуйте: /admin_keys generate <план> [количество]")

    elif args.startswith("list"):
        try:
            parts = args.split()
            if len(parts) < 2:
                await message.answer("❌ Используйте: /admin_keys list <план> [used/all/new]")
                return

            plan_name = parts[1].upper()
            filter_type = parts[2] if len(parts) > 2 else "new"

            used_filter = None
            if filter_type == "used":
                used_filter = True
            elif filter_type == "new":
                used_filter = False

            keys = await database.get_all_keys(plan_name=plan_name, used=used_filter, limit=50)

            if not keys:
                await message.answer(f"📭 Нет ключей для плана {plan_name} ({filter_type})")
                return

            keys_text = f"🔑 Ключи плана {plan_name} ({filter_type}):\n\n"

            for key in keys[:20]:
                status = "✅" if not key['is_used'] else "❌"
                used_by = f"👤 {key.get('full_name', 'Unknown')}" if key['is_used'] else "🆕 Новый"
                keys_text += f"{status} <code>{key['key_code']}</code> - {used_by}\n"

            if len(keys) > 20:
                keys_text += f"\n... и еще {len(keys) - 20} ключей"

            await message.answer(keys_text, parse_mode="HTML")

        except (IndexError, ValueError) as e:
            await message.answer(f"❌ Ошибка: {e}")

    elif args.startswith("check"):
        try:
            key_code = args.split(maxsplit=1)[1].upper()
            validation = await database.validate_key(key_code)

            if validation['valid']:
                used_by = f"👤 Использован пользователем" if validation.get('used_by') else "🆕 Не использован"
                expires = f"📅 Истекает: {validation.get('expires_at', 'N/A')[:10]}" if validation.get(
                    'expires_at') else "⏳ Бессрочный"

                check_text = (
                    f"✅ Ключ валиден!\n\n"
                    f"🔑 Ключ: <code>{key_code}</code>\n"
                    f"💎 План: {validation['plan_name']}\n"
                    f"📋 Описание: {validation['description']}\n"
                    f"💰 Цена: {validation['price']}$\n"
                    f"📊 Лимит: {validation['max_requests']} запр.\n"
                    f"📅 Создан: {validation.get('created_at', 'N/A')[:10]}\n"
                    f"{expires}\n"
                    f"📊 Статус: {used_by}"
                )
            else:
                check_text = f"❌ Ключ невалиден: {validation['error']}"

            await message.answer(check_text, parse_mode="HTML")

        except IndexError:
            await message.answer("❌ Используйте: /admin_keys check <ключ>")

    elif args == "stats":
        keys = await database.get_all_keys(limit=1000)

        if not keys:
            await message.answer("📭 Нет ключей в системе")
            return

        total = len(keys)
        used = sum(1 for k in keys if k['is_used'])
        new = total - used

        # Статистика по планам
        plans_stats = {}
        for key in keys:
            plan = key['plan_name']
            if plan not in plans_stats:
                plans_stats[plan] = {'total': 0, 'used': 0}
            plans_stats[plan]['total'] += 1
            if key['is_used']:
                plans_stats[plan]['used'] += 1

        stats_text = f"📊 Статистика ключей:\n\n"
        stats_text += f"🔑 Всего ключей: {total}\n"
        stats_text += f"✅ Использовано: {used}\n"
        stats_text += f"🆕 Доступно: {new}\n\n"

        stats_text += "💎 По планам:\n"
        for plan, stats in plans_stats.items():
            stats_text += f"• {plan}: {stats['used']}/{stats['total']} (использовано/всего)\n"

        await message.answer(stats_text)

    elif args.startswith("user"):
        try:
            user_id = int(args.split()[1])
            key_data = await database.get_user_active_key(user_id)

            if key_data:
                user = await database.get_user(user_id=user_id)

                user_info = (
                    f"👤 Пользователь: {user['full_name']} (@{user.get('username', 'нет')})\n"
                    f"🔑 Ключ: <code>{key_data['key_code']}</code>\n"
                    f"💎 План: {key_data['plan_name']}\n"
                    f"📅 Активирован: {key_data['used_at'][:10] if key_data['used_at'] else 'N/A'}\n"
                    f"📅 Создан: {key_data['created_at'][:10]}"
                )
            else:
                user_info = f"❌ У пользователя {user_id} нет активного ключа"

            await message.answer(user_info, parse_mode="HTML")

        except (IndexError, ValueError):
            await message.answer("❌ Используйте: /admin_keys user <user_id>")


# Обработчики callback-кнопок
@router.callback_query(F.data == "confirm_deactivate_key")
async def callback_confirm_deactivate(callback: CallbackQuery):
    """Подтверждение отвязки ключа"""
    success = await database.deactivate_user_key(callback.from_user.id)

    if success:
        await callback.message.edit_text(
            "✅ Ключ успешно отвязан!\n\n"
            "📋 Вы переведены на FREE план (50 запросов/мес).\n"
            "🔑 Старый ключ отмечен как использованный.\n\n"
            "💎 Для активации нового ключа используйте /activate"
        )
    else:
        await callback.message.edit_text(
            "❌ Не удалось отвязать ключ.\n"
            "Возможно, у вас нет активного ключа."
        )

    await callback.answer()


@router.callback_query(F.data == "cancel_deactivate_key")
async def callback_cancel_deactivate(callback: CallbackQuery):
    """Отмена отвязки ключа"""
    await callback.message.edit_text("❌ Отвязка ключа отменена.")
    await callback.answer()


@router.callback_query(F.data == "deactivate_key")
async def callback_deactivate_key(callback: CallbackQuery):
    """Обработка нажатия на кнопку отвязки ключа"""
    await cmd_deactivate(callback.message)
    await callback.answer()


@router.callback_query(F.data == "replace_key")
async def callback_replace_key(callback: CallbackQuery):
    """Обработка нажатия на кнопку замены ключа"""
    await cmd_replace_key(callback.message)
    await callback.answer()


@router.callback_query(F.data == "key_status")
async def callback_key_status(callback: CallbackQuery):
    """Обработка нажатия на кнопку статуса ключа"""
    await cmd_key_status(callback.message)
    await callback.answer()


@router.callback_query(F.data == "activate_key")
async def callback_activate_key(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия на кнопку активации"""
    await cmd_activate(callback.message, state)
    await callback.answer()
from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, CallbackQuery
from database.db import database
from keyboards.reply import get_links_menu_keyboard, get_categories_keyboard
from keyboards.inline import get_link_actions_keyboard

router = Router()


class LinkStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_category = State()
    waiting_for_link_edit = State()
    waiting_for_search = State()


@router.message(Command("links"))
async def cmd_links(message: types.Message):
    """Меню управления ссылками"""
    # Проверяем доступ пользователя
    access_check = await database.check_user_access(message.from_user.id)

    if not access_check['has_access']:
        await message.answer(
            f"❌ Доступ запрещен!\n"
            f"Причина: {access_check['reason']}\n\n"
            f"💎 Используйте /activate для активации ключа"
        )
        return

    await message.answer(
        "🔗 Управление ссылками\n\n"
        "Выберите действие:",
        reply_markup=get_links_menu_keyboard()
    )


@router.message(F.text == "📥 Добавить ссылку")
async def add_link_start(message: types.Message, state: FSMContext):
    """Начало добавления ссылки"""
    await message.answer(
        "📝 Введите URL ссылки:\n\n"
        "Пример: https://example.com\n"
        "❌ Для отмены введите /cancel",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(LinkStates.waiting_for_url)


@router.message(LinkStates.waiting_for_url)
async def process_link_url(message: types.Message, state: FSMContext):
    """Обработка URL ссылки"""
    if message.text.lower() == '/cancel':
        await state.clear()
        await message.answer("❌ Добавление ссылки отменено",
                             reply_markup=get_links_menu_keyboard())
        return

    url = message.text.strip()

    # Простая валидация URL
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'https://' + url

    # Сохраняем URL в состоянии
    await state.update_data(url=url)

    await message.answer(
        "📝 Введите заголовок ссылки (необязательно):\n\n"
        "Пример: Мой любимый сайт\n"
        "❌ Пропустить - отправьте /skip\n"
        "❌ Отмена - /cancel"
    )
    await state.set_state(LinkStates.waiting_for_title)


@router.message(LinkStates.waiting_for_title)
async def process_link_title(message: types.Message, state: FSMContext):
    """Обработка заголовка ссылки"""
    if message.text.lower() == '/cancel':
        await state.clear()
        await message.answer("❌ Добавление ссылки отменено",
                             reply_markup=get_links_menu_keyboard())
        return

    title = None
    if message.text.lower() != '/skip':
        title = message.text.strip()[:100]  # Ограничиваем длину

    # Сохраняем заголовок в состоянии
    await state.update_data(title=title)

    await message.answer(
        "📝 Введите описание ссылки (необязательно):\n\n"
        "Пример: Этот сайт содержит полезные материалы\n"
        "❌ Пропустить - отправьте /skip\n"
        "❌ Отмена - /cancel"
    )
    await state.set_state(LinkStates.waiting_for_description)


@router.message(LinkStates.waiting_for_description)
async def process_link_description(message: types.Message, state: FSMContext):
    """Обработка описания ссылки"""
    if message.text.lower() == '/cancel':
        await state.clear()
        await message.answer("❌ Добавление ссылки отменено",
                             reply_markup=get_links_menu_keyboard())
        return

    description = None
    if message.text.lower() != '/skip':
        description = message.text.strip()[:500]  # Ограничиваем длину

    # Сохраняем описание в состоянии
    await state.update_data(description=description)

    # Получаем категории пользователя
    categories = await database.get_link_categories(message.from_user.id)

    if categories:
        await message.answer(
            "📁 Выберите категорию из существующих или введите новую:\n\n"
            f"Существующие категории: {', '.join(categories)}\n\n"
            "❌ Пропустить (будет использована категория 'general') - /skip\n"
            "❌ Отмена - /cancel",
            reply_markup=get_categories_keyboard(categories)
        )
    else:
        await message.answer(
            "📁 Введите категорию ссылки (необязательно):\n\n"
            "Пример: work, personal, shopping\n"
            "❌ Пропустить (будет использована категория 'general') - /skip\n"
            "❌ Отмена - /cancel"
        )

    await state.set_state(LinkStates.waiting_for_category)


@router.message(LinkStates.waiting_for_category)
async def process_link_category(message: types.Message, state: FSMContext):
    """Обработка категории ссылки"""
    if message.text.lower() == '/cancel':
        await state.clear()
        await message.answer("❌ Добавление ссылки отменено",
                             reply_markup=get_links_menu_keyboard())
        return

    category = 'general'
    if message.text.lower() != '/skip':
        category = message.text.strip().lower()[:50]

    # Получаем данные из состояния
    data = await state.get_data()
    url = data.get('url')
    title = data.get('title')
    description = data.get('description')

    # Добавляем ссылку в базу
    link_id = await database.add_user_link(
        user_id=message.from_user.id,
        url=url,
        title=title,
        description=description,
        category=category
    )

    # Формируем сообщение о результате
    result_message = f"✅ Ссылка успешно добавлена!\n\n"
    result_message += f"🔗 URL: {url}\n"
    if title:
        result_message += f"📝 Заголовок: {title}\n"
    if description:
        result_message += f"📄 Описание: {description[:50]}...\n" if len(
            description) > 50 else f"📄 Описание: {description}\n"
    result_message += f"📁 Категория: {category}\n"
    result_message += f"🆔 ID: {link_id}"

    await message.answer(
        result_message,
        reply_markup=get_links_menu_keyboard()
    )

    # Показываем статистику
    link_count = await database.get_user_link_count(message.from_user.id)
    await message.answer(
        f"📊 Всего сохранено ссылок: {link_count}\n"
        f"💾 Используйте /my_links для просмотра"
    )

    await state.clear()


@router.message(F.text == "📋 Мои ссылки")
async def show_my_links(message: types.Message):
    """Показать ссылки пользователя"""
    # Проверяем доступ
    access_check = await database.check_user_access(message.from_user.id)
    if not access_check['has_access']:
        await message.answer("❌ Нет доступа. Активируйте ключ через /activate")
        return

    # Получаем категории
    categories = await database.get_link_categories(message.from_user.id)

    if not categories:
        await message.answer(
            "📭 У вас пока нет сохраненных ссылок.\n\n"
            "📥 Используйте 'Добавить ссылку' для начала."
        )
        return

    # Показываем категории
    categories_text = "📁 Ваши категории ссылок:\n\n"
    for i, category in enumerate(categories, 1):
        count = await database.get_user_link_count(message.from_user.id, category)
        categories_text += f"{i}. {category} - {count} ссылок\n"

    categories_text += "\n🔍 Для просмотра ссылок в категории отправьте её название."

    await message.answer(categories_text)


@router.message(F.text.in_(["🔍 Поиск ссылок", "поиск"]))
async def search_links_start(message: types.Message, state: FSMContext):
    """Начало поиска ссылок"""
    await message.answer(
        "🔍 Введите поисковый запрос:\n\n"
        "Ищет по URL, заголовку, описанию и категории.\n"
        "❌ Для отмены введите /cancel",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(LinkStates.waiting_for_search)


@router.message(LinkStates.waiting_for_search)
async def process_search_links(message: types.Message, state: FSMContext):
    """Обработка поискового запроса"""
    if message.text.lower() == '/cancel':
        await state.clear()
        await message.answer("❌ Поиск отменен",
                             reply_markup=get_links_menu_keyboard())
        return

    search_query = message.text.strip()

    if len(search_query) < 2:
        await message.answer("❌ Запрос должен содержать минимум 2 символа")
        return

    # Ищем ссылки
    links = await database.search_user_links(message.from_user.id, search_query, limit=10)

    if not links:
        await message.answer(
            f"🔍 По запросу '{search_query}' ничего не найдено.",
            reply_markup=get_links_menu_keyboard()
        )
        await state.clear()
        return

    # Показываем результаты
    results_text = f"🔍 Результаты поиска '{search_query}':\n\n"

    for i, link in enumerate(links[:5], 1):  # Показываем первые 5
        title = link['title'] or 'Без названия'
        results_text += f"{i}. {title}\n"
        results_text += f"   🔗 {link['url'][:50]}...\n"
        if link['description']:
            results_text += f"   📄 {link['description'][:50]}...\n"
        results_text += f"   📁 {link['category']}\n\n"

    if len(links) > 5:
        results_text += f"📊 ... и еще {len(links) - 5} ссылок\n\n"

    results_text += "📝 Для действий с ссылкой используйте команду /link <id>"

    await message.answer(
        results_text,
        reply_markup=get_links_menu_keyboard()
    )

    await state.clear()


@router.message(Command("my_links"))
async def cmd_my_links(message: types.Message, command: CommandObject = None):
    """Просмотр ссылок пользователя с пагинацией"""
    # Проверяем доступ
    access_check = await database.check_user_access(message.from_user.id)
    if not access_check['has_access']:
        await message.answer("❌ Нет доступа. Активируйте ключ через /activate")
        return

    # Парсим аргументы
    args = command.args if command else None
    category = None
    page = 1

    if args:
        parts = args.split()
        if parts:
            category = parts[0]
            if len(parts) > 1 and parts[1].isdigit():
                page = int(parts[1])

    # Определяем лимит и смещение
    limit = 10
    offset = (page - 1) * limit

    # Получаем ссылки
    links = await database.get_user_links(
        user_id=message.from_user.id,
        category=category,
        limit=limit,
        offset=offset
    )

    if not links:
        if category:
            await message.answer(f"📭 В категории '{category}' нет ссылок.")
        else:
            await message.answer(
                "📭 У вас пока нет сохраненных ссылок.\n\n"
                "📥 Используйте 'Добавить ссылку' для начала."
            )
        return

    # Формируем сообщение
    total_count = await database.get_user_link_count(message.from_user.id, category)
    total_pages = (total_count + limit - 1) // limit

    if category:
        header = f"📁 Ссылки в категории '{category}' (стр. {page}/{total_pages}):\n\n"
    else:
        header = f"🔗 Все ваши ссылки (стр. {page}/{total_pages}):\n\n"

    links_text = header

    for i, link in enumerate(links, offset + 1):
        title = link['title'] or 'Без названия'
        links_text += f"{i}. {title}\n"
        links_text += f"   🔗 {link['url']}\n"
        if link['description']:
            desc = link['description']
            links_text += f"   📄 {desc[:50]}...\n" if len(desc) > 50 else f"   📄 {desc}\n"
        links_text += f"   📁 {link['category']} | 🆔 {link['id']}\n\n"

    links_text += f"📊 Всего: {total_count} ссылок\n"

    # Добавляем навигацию
    navigation = ""
    if page > 1:
        navigation += f"⬅️ /my_links {category if category else ''} {page - 1} "
    if page < total_pages:
        navigation += f"➡️ /my_links {category if category else ''} {page + 1}"

    if navigation:
        links_text += f"\n📑 Навигация: {navigation}"

    await message.answer(links_text)


@router.message(Command("link"))
async def cmd_link_actions(message: types.Message, command: CommandObject):
    """Действия с конкретной ссылкой"""
    if not command or not command.args:
        await message.answer(
            "🛠️ Действия с ссылкой:\n\n"
            "Используйте: /link <id>\n"
            "Пример: /link 1\n\n"
            "📋 Для просмотра всех ссылок: /my_links"
        )
        return

    try:
        link_id = int(command.args.split()[0])

        # Получаем информацию о ссылке
        # Для простоты получим все и отфильтруем
        all_links = await database.get_user_links(message.from_user.id, limit=100)
        link = next((l for l in all_links if l['id'] == link_id), None)

        if not link:
            await message.answer(f"❌ Ссылка с ID {link_id} не найдена.")
            return

        # Формируем информацию о ссылке
        link_info = f"🔗 Ссылка #{link_id}\n\n"
        link_info += f"📝 Заголовок: {link['title'] or 'Не указан'}\n"
        link_info += f"🌐 URL: {link['url']}\n"
        if link['description']:
            link_info += f"📄 Описание: {link['description']}\n"
        link_info += f"📁 Категория: {link['category']}\n"
        link_info += f"📅 Добавлена: {link['created_at'][:10]}\n"
        link_info += f"✅ Статус: {'Активна' if link['is_active'] else 'Неактивна'}"

        await message.answer(
            link_info,
            reply_markup=get_link_actions_keyboard(link_id)
        )

    except ValueError:
        await message.answer("❌ Неверный ID. ID должен быть числом.")


@router.message(F.text == "📊 Статистика ссылок")
async def show_links_stats(message: types.Message):
    """Статистика по ссылкам"""
    # Проверяем доступ
    access_check = await database.check_user_access(message.from_user.id)
    if not access_check['has_access']:
        await message.answer("❌ Нет доступа. Активируйте ключ через /activate")
        return

    # Получаем категории и количество ссылок в каждой
    categories = await database.get_link_categories(message.from_user.id)
    total_count = await database.get_user_link_count(message.from_user.id)

    if total_count == 0:
        await message.answer("📊 У вас пока нет сохраненных ссылок.")
        return

    stats_text = f"📊 Статистика ваших ссылок:\n\n"
    stats_text += f"🔗 Всего ссылок: {total_count}\n\n"

    if categories:
        stats_text += "📁 Распределение по категориям:\n"
        for category in categories:
            count = await database.get_user_link_count(message.from_user.id, category)
            percentage = (count / total_count) * 100
            stats_text += f"• {category}: {count} ({percentage:.1f}%)\n"

    # Получаем последние добавленные ссылки
    recent_links = await database.get_user_links(message.from_user.id, limit=3)

    if recent_links:
        stats_text += "\n📅 Последние добавленные:\n"
        for link in recent_links:
            title = link['title'] or 'Без названия'
            stats_text += f"• {title[:30]}... ({link['created_at'][:10]})\n"

    await message.answer(stats_text)


@router.message(F.text == "📤 Экспорт ссылок")
async def export_links(message: types.Message):
    """Экспорт ссылок в текстовый формат"""
    # Проверяем доступ
    access_check = await database.check_user_access(message.from_user.id)
    if not access_check['has_access']:
        await message.answer("❌ Нет доступа. Активируйте ключ через /activate")
        return

    # Получаем все ссылки
    links = await database.get_user_links(message.from_user.id, limit=1000)

    if not links:
        await message.answer("📭 Нет ссылок для экспорта.")
        return

    # Формируем текстовый файл
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"links_export_{timestamp}.txt"

    export_text = f"Экспорт ссылок пользователя {message.from_user.full_name}\n"
    export_text += f"Дата экспорта: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    export_text += f"Всего ссылок: {len(links)}\n"
    export_text += "=" * 50 + "\n\n"

    for i, link in enumerate(links, 1):
        export_text += f"{i}. {link['title'] or 'Без названия'}\n"
        export_text += f"   URL: {link['url']}\n"
        if link['description']:
            export_text += f"   Описание: {link['description']}\n"
        export_text += f"   Категория: {link['category']}\n"
        export_text += f"   Добавлена: {link['created_at']}\n"
        export_text += "\n"

    # Сохраняем в файл
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(export_text)

    # Отправляем файл пользователю
    await message.answer_document(
        types.FSInputFile(filename),
        caption=f"📤 Экспорт ссылок ({len(links)} шт.)"
    )


@router.message(F.text == "🏠 Главное меню")
async def back_to_main_menu(message: types.Message):
    """Возврат в главное меню"""
    from keyboards.reply import get_main_menu
    await message.answer(
        "🏠 Главное меню\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu()
    )


# Обработчики callback-кнопок
@router.callback_query(F.data.startswith("edit_link_"))
async def callback_edit_link(callback: CallbackQuery, state: FSMContext):
    """Редактирование ссылки"""
    try:
        link_id = int(callback.data.replace("edit_link_", ""))
        await callback.message.answer(
            f"✏️ Редактирование ссылки #{link_id}\n\n"
            f"Введите новые данные в формате:\n"
            f"<code>title|description|category</code>\n\n"
            f"Пример: Новый заголовок|Новое описание|новая_категория\n\n"
            f"❌ Для отмены введите /cancel",
            parse_mode="HTML"
        )
        await state.set_data({'link_id': link_id})
        await state.set_state(LinkStates.waiting_for_link_edit)
        await callback.answer()
    except ValueError:
        await callback.answer("❌ Ошибка: неверный ID ссылки")


@router.callback_query(F.data.startswith("delete_link_"))
async def callback_delete_link(callback: CallbackQuery):
    """Удаление ссылки"""
    try:
        link_id = int(callback.data.replace("delete_link_", ""))
        success = await database.delete_user_link(link_id, callback.from_user.id)

        if success:
            await callback.message.edit_text(
                f"✅ Ссылка #{link_id} успешно удалена!"
            )
        else:
            await callback.message.edit_text(
                f"❌ Не удалось удалить ссылку #{link_id}"
            )
        await callback.answer()
    except ValueError:
        await callback.answer("❌ Ошибка: неверный ID ссылки")
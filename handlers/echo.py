from aiogram import Router, types
from database.db import database

router = Router()


@router.message()
async def echo_message(message: types.Message):
    # Сохраняем сообщение в БД как запрос пользователя
    await database.add_user_request(
        user_id=message.from_user.id,
        request_type="echo_message",
        request_data=message.text,
        response_data=f"Echo: {message.text}",
        tokens_used=0
    )

    # Увеличиваем счетчик запросов пользователя
    await database.increment_user_requests(message.from_user.id)

    # Отвечаем пользователю
    await message.answer(
        f"Вы написали: {message.text}\n\n"
        f"✅ Сообщение сохранено в базе данных!\n"
        f"📊 Это запись в вашей истории запросов."
    )
from aiogram import Router, types
from database.db import database

router = Router()


@router.message()
async def echo_message(message: types.Message):
    # Сохраняем сообщение в БД
    await database.add_message(
        user_id=message.from_user.id,
        text=message.text
    )

    # Отвечаем пользователю
    await message.answer(
        f"Вы написали: {message.text}\n\n"
        f"Сообщение сохранено в базе данных!"
    )
from aiogram import Router, types
from aiogram.filters import CommandStart
from database.db import database
from keyboards.inline import get_start_keyboard
from keyboards.reply import get_main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    # Добавляем пользователя в БД
    await database.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    await message.answer(
        f"Привет, {message.from_user.full_name}!\n"
        f"Добро пожаловать в бота на aiogram 3.x!\n\n"
        f"ID: {message.from_user.id}",
        reply_markup=get_start_keyboard()
    )

    # Показываем основное меню
    await message.answer(
        "Выберите действие:",
        reply_markup=get_main_menu()
    )


@router.callback_query(lambda c: c.data == "delete_message")
async def delete_message(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer("Сообщение удалено!")
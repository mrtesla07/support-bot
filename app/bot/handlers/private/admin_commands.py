from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command, MagicData
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold, hlink

from app.bot.manager import Manager
from app.bot.utils.redis import RedisStorage
from app.bot.utils.redis.models import UserData


router = Router(name="admin_commands")
router.message.filter(
    F.chat.type == "private",
    MagicData(F.event_from_user.id == F.config.bot.DEV_ID),  # type: ignore[attr-defined]
)
router.callback_query.filter(
    F.message.chat.type == "private",
    MagicData(F.event_from_user.id == F.config.bot.DEV_ID),  # type: ignore[attr-defined]
)


async def _send_banned_users(manager: Manager, redis: RedisStorage) -> None:
    """
    Show all banned users with unban buttons.
    
    :param manager: Manager object.
    :param redis: RedisStorage object.
    :return: None
    """
    banned_users = await redis.get_banned_users()
    
    if not banned_users:
        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️ Назад", callback_data="admin:menu")
        await manager.send_message(
            "Забаненных пользователей нет.",
            reply_markup=builder.as_markup(),
            replace_previous=False,
        )
        return
    
    # Create a message with inline keyboard for each user
    text_parts = ["Забаненные пользователи:"]
    builder = InlineKeyboardBuilder()
    
    for i, user_data in enumerate(banned_users):
        user_link = hlink(user_data.full_name, f"tg://user?id={user_data.id}")
        text_parts.append(f"{i+1}. {user_link} (ID: {user_data.id})")
        builder.button(text=f"Разбанить {user_data.full_name}", callback_data=f"unban_user_{user_data.id}")
    
    builder.button(text="⬅️ Назад", callback_data="admin:menu")
    builder.adjust(1)  # One button per row
    text = "\n".join(text_parts)
    
    await manager.send_message(text, reply_markup=builder.as_markup(), replace_previous=False)


@router.message(Command("banned"))
async def show_banned_users(message: Message, manager: Manager, redis: RedisStorage) -> None:
    await _send_banned_users(manager, redis)
    await manager.delete_message(message)


@router.callback_query(F.data == "admin:banned")
async def show_banned_users_callback(call: CallbackQuery, manager: Manager, redis: RedisStorage) -> None:
    await _send_banned_users(manager, redis)
    await call.answer()


@router.callback_query(F.data.startswith("unban_user_"))
async def unban_user_callback(call: CallbackQuery, manager: Manager, redis: RedisStorage) -> None:
    """
    Handle unban button clicks.
    
    :param call: CallbackQuery object.
    :param manager: Manager object.
    :param redis: RedisStorage object.
    :return: None
    """
    user_id = int(call.data.split("_")[-1])
    
    # Get user data
    user_data = await redis.get_user(user_id)
    if not user_data:
        await call.answer("Пользователь не найден.", show_alert=True)
        return
    
    if not user_data.is_banned:
        await call.answer("Пользователь уже разбанен.", show_alert=True)
        return
    
    # Unban the user
    user_data.is_banned = False
    await redis.update_user(user_id, user_data)
    
    await call.answer(f"Пользователь {hbold(user_data.full_name)} (ID: {user_id}) разбанен.")
    await _send_banned_users(manager, redis)


@router.message(Command("unban"))
async def unban_user_command(message: Message, manager: Manager, redis: RedisStorage) -> None:
    """
    Unban a user by ID provided in the command (fallback method).
    
    :param message: Message object.
    :param manager: Manager object.
    :param redis: RedisStorage object.
    :return: None
    """
    # Get the user ID from the command arguments
    command_args = message.text.split()
    if len(command_args) != 2:
        await message.reply("Использование: /unban <user_id>")
        return
    
    try:
        user_id = int(command_args[1])
    except ValueError:
        await message.reply("ID пользователя должен быть числом.")
        return
    
    # Get user data
    user_data = await redis.get_user(user_id)
    if not user_data:
        await message.reply(f"Пользователь с ID {user_id} не найден.")
        return
    
    if not user_data.is_banned:
        await message.reply(f"Пользователь {hbold(user_data.full_name)} (ID: {user_id}) не забанен.")
        return
    
    # Unban the user
    user_data.is_banned = False
    await redis.update_user(user_id, user_data)
    
    await manager.send_message(f"Пользователь {hbold(user_data.full_name)} (ID: {user_id}) разбанен.")
    await manager.delete_message(message)

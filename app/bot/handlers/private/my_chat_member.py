from aiogram import Router, F
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMemberUpdated
from aiogram.utils.markdown import hlink
from aiogram.exceptions import TelegramBadRequest

from app.bot.manager import Manager
from app.bot.utils.redis import RedisStorage
from app.bot.utils.redis.models import UserData
from app.bot.utils.security import sanitize_display_name
from app.bot.utils.create_forum_topic import create_forum_topic

router = Router()
router.my_chat_member.filter(F.chat.type == "private")


@router.my_chat_member()
async def handle_chat_member_update(
        update: ChatMemberUpdated,
        redis: RedisStorage,
        user_data: UserData,
        manager: Manager,
) -> None:
    """
    Handle updates of the bot chat member status.

    :param update: ChatMemberUpdated object.
    :param redis: RedisStorage object.
    :param user_data: UserData object.
    :param manager: Manager object.
    :return: None
    """
    # Update the user's state based on the new chat member status
    user_data.state = update.new_chat_member.status
    await redis.update_user(user_data.id, user_data)

    if user_data.state == ChatMemberStatus.MEMBER:
        text = manager.text_message.get("user_restarted_bot")
    else:
        text = manager.text_message.get("user_stopped_bot")

    url = f"https://t.me/{user_data.username[1:]}" if user_data.username != "-" else f"tg://user?id={user_data.id}"
    safe_name = sanitize_display_name(user_data.full_name, placeholder=f"User {user_data.id}")

    if user_data.message_thread_id is None:
        user_data.message_thread_id = await create_forum_topic(
            update.bot,
            manager.config,
            user_data.full_name,
        )
        await redis.update_user(user_data.id, user_data)

    try:
        await update.bot.send_message(
            chat_id=manager.config.bot.GROUP_ID,
            text=text.format(name=hlink(safe_name, url)),
            message_thread_id=user_data.message_thread_id,
        )
    except TelegramBadRequest as ex:
        if "message thread not found" not in ex.message.lower():
            raise

        user_data.message_thread_id = await create_forum_topic(
            update.bot,
            manager.config,
            user_data.full_name,
        )
        await redis.update_user(user_data.id, user_data)
        await update.bot.send_message(
            chat_id=manager.config.bot.GROUP_ID,
            text=text.format(name=hlink(safe_name, url)),
            message_thread_id=user_data.message_thread_id,
        )

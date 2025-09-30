from datetime import datetime, timezone
import re
from contextlib import suppress

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.bot.manager import Manager
from app.bot.types.album import Album
from app.bot.utils.create_forum_topic import (
    create_forum_topic,
    get_or_create_forum_topic,
)
from app.bot.utils.redis import RedisStorage
from app.bot.utils.redis.models import UserData
from app.bot.utils.reminders import schedule_support_reminder

GRATITUDE_PHRASES = {
    'спасибо',
    'спасибо большое',
    'спасибо за помощь',
    'благодарю',
    'thank you',
    'thanks',
    'thx',
}


router = Router()
router.message.filter(F.chat.type == "private", StateFilter(None))


@router.edited_message()
async def handle_edited_message(message: Message, manager: Manager) -> None:
    """
    Handle edited messages.

    :param message: The edited message.
    :param manager: Manager object.
    :return: None
    """
    # Get the text for the edited message
    text = manager.text_message.get("message_edited")
    # Reply with a short-lived confirmation
    msg = await message.reply(text)
    Manager.schedule_message_cleanup(msg)


@router.message(F.media_group_id)
@router.message(F.media_group_id.is_(None))
async def handle_incoming_message(
        message: Message,
        manager: Manager,
        redis: RedisStorage,
        user_data: UserData,
        apscheduler: AsyncIOScheduler,
        album: Album | None = None,
) -> None:
    """
    Handles incoming messages and copies them to the forum topic.
    If the user is banned, the messages are ignored.

    :param message: The incoming message.
    :param manager: Manager object.
    :param redis: RedisStorage object.
    :param user_data: UserData object.
    :param album: Album object or None.
    :return: None
    """
    # Check if the user is banned
    if user_data.is_banned:
        return

    async def copy_message_to_topic():
        """
        Copies the message or album to the forum topic.
        If no album is provided, the message is copied. Otherwise, the album is copied.
        """
        message_thread_id = await get_or_create_forum_topic(
            message.bot,
            redis,
            manager.config,
            user_data,
        )

        if not album:
            await message.forward(
                chat_id=manager.config.bot.GROUP_ID,
                message_thread_id=message_thread_id,
            )
        else:
            await album.copy_to(
                chat_id=manager.config.bot.GROUP_ID,
                message_thread_id=message_thread_id,
            )

    try:
        await copy_message_to_topic()
    except TelegramBadRequest as ex:
        if "message thread not found" in ex.message:
            user_data.message_thread_id = await create_forum_topic(
                message.bot,
                manager.config,
                user_data.full_name,
            )
            await redis.update_user(user_data.id, user_data)
            await copy_message_to_topic()
        else:
            raise

    # Send a confirmation message to the user
    text = manager.text_message.get("message_sent")
    msg = await message.reply(text)
    Manager.schedule_message_cleanup(msg)

    ticket_was_resolved = user_data.ticket_status == "resolved"

    text_content = message.text or message.caption or ""
    normalized = re.sub(r'[\W_]+', ' ', text_content.lower()).strip()
    if user_data.ticket_status == "resolved" and normalized in GRATITUDE_PHRASES:
        user_data.awaiting_reply = False
        await redis.update_user(user_data.id, user_data)
        return

    user_data.ticket_status = "open"
    user_data.awaiting_reply = True
    user_data.last_user_message_at = datetime.now(timezone.utc).isoformat()
    await redis.update_user(user_data.id, user_data)

    if ticket_was_resolved and user_data.message_thread_id is not None:
        with suppress(TelegramBadRequest):
            await message.bot.edit_forum_topic(
                chat_id=manager.config.bot.GROUP_ID,
                message_thread_id=user_data.message_thread_id,
                icon_custom_emoji_id=manager.config.bot.BOT_EMOJI_ID,
            )

    schedule_support_reminder(
        apscheduler,
        bot_token=manager.config.bot.TOKEN,
        group_id=manager.config.bot.GROUP_ID,
        user_id=user_data.id,
        message_thread_id=user_data.message_thread_id,
        language_code=user_data.language_code,
        redis_dsn=manager.config.redis.dsn(),
    )


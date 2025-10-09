import asyncio
from datetime import datetime, timezone

import re
from contextlib import suppress

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram.utils.markdown import hlink
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
from app.bot.utils.security import analyze_user_message, sanitize_display_name

TOPIC_ICON_RESTORE_DELAY = 3.0

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

    text_content = message.text or message.caption or ""

    def entities_contain_links(msg: Message) -> bool:
        for container in (msg.entities or [], msg.caption_entities or []):
            for entity in container:
                if entity.type in {"url", "text_link"}:
                    return True
        return False

    suspicion = analyze_user_message(
        full_name=user_data.full_name,
        username=user_data.username,
        message_text=text_content,
        entities_contains_link=entities_contain_links(message),
    )

    if suspicion.should_block:
        user_data.is_banned = True
        user_data.awaiting_reply = False
        await redis.update_user(user_data.id, user_data)

        reason_text = "; ".join(suspicion.reasons())
        await message.reply(
            manager.text_message.get("auto_blocked_notice").format(reason=reason_text),
        )

        thread_id = user_data.message_thread_id
        group_kwargs = {"message_thread_id": thread_id} if thread_id is not None else {}
        safe_name = sanitize_display_name(user_data.full_name, placeholder=f"User {user_data.id}")
        await message.bot.send_message(
            chat_id=manager.config.bot.GROUP_ID,
            text=manager.text_message.get("auto_blocked_alert").format(
                user=hlink(safe_name, f"tg://user?id={user_data.id}"),
                reason=reason_text,
            ),
            disable_web_page_preview=True,
            **group_kwargs,
        )
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
        thread_id = user_data.message_thread_id
        group_id = manager.config.bot.GROUP_ID
        bot = message.bot
        icon_id = manager.config.bot.BOT_EMOJI_ID

        async def restore_topic_icon() -> None:
            await asyncio.sleep(TOPIC_ICON_RESTORE_DELAY)
            with suppress(TelegramBadRequest):
                await bot.edit_forum_topic(
                    chat_id=group_id,
                    message_thread_id=thread_id,
                    icon_custom_emoji_id=icon_id,
                )

        asyncio.create_task(restore_topic_icon())

    schedule_support_reminder(
        apscheduler,
        bot_token=manager.config.bot.TOKEN,
        group_id=manager.config.bot.GROUP_ID,
        user_id=user_data.id,
        message_thread_id=user_data.message_thread_id,
        language_code=user_data.language_code,
        redis_dsn=manager.config.redis.dsn(),
    )


from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramBadRequest

from app.bot.utils.security import sanitize_display_name

if TYPE_CHECKING:
    from .manager import MigrationContext

logger = logging.getLogger(__name__)


async def sanitize_existing_display_names(context: "MigrationContext") -> None:
    user_ids = await context.storage.get_all_users_ids()
    if not user_ids:
        return

    for user_id in user_ids:
        user_data = await context.storage.get_user(user_id)
        if not user_data:
            continue

        placeholder = f"User {user_data.id}"
        sanitized_full_name = sanitize_display_name(user_data.full_name, placeholder=placeholder)

        needs_update = sanitized_full_name != user_data.full_name
        if needs_update:
            logger.debug("Updating stored name for user %s -> %s", user_id, sanitized_full_name)
            user_data.full_name = sanitized_full_name
            await context.storage.update_user(user_id, user_data)

        if user_data.message_thread_id is None:
            continue

        if needs_update:
            with suppress(TelegramBadRequest):
                await context.bot.edit_forum_topic(
                    chat_id=context.config.bot.GROUP_ID,
                    message_thread_id=user_data.message_thread_id,
                    name=sanitized_full_name,
                )
                await context.sleep()

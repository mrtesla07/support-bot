from __future__ import annotations

import logging

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import MigrationContext

logger = logging.getLogger(__name__)


async def ensure_operator_replied_flag(context: 'MigrationContext') -> None:
    user_ids = await context.storage.get_all_users_ids()
    logger.info("Updating %s users with missing operator_replied flag.", len(user_ids))
    for user_id in user_ids:
        user = await context.storage.get_user(user_id)
        if user is None:
            continue
        if getattr(user, "operator_replied", None) is None:
            user.operator_replied = False
            await context.storage.update_user(user.id, user)
        await context.sleep()

from contextlib import suppress
from typing import Any, Awaitable, Callable, Dict, MutableMapping, Optional

from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import Message, TelegramObject, User
from cachetools import TTLCache


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware for handling throttling.
    """

    def __init__(
            self,
            *,
            default_key: Optional[str] = "default",
            default_ttl: float = 0.05,
            **ttl_map: float,
    ) -> None:
        """
        Initialize the ThrottlingMiddleware.

        :param default_key: The default key for throttling.
        :param default_ttl: The default time-to-live (TTL) in seconds for the default key.
        :param ttl_map: Mapping of keys to corresponding TTL values.
        """
        if default_key:
            ttl_map[default_key] = default_ttl
        self.default_key = default_key
        self.caches: Dict[str, MutableMapping[int, None]] = {}
        for name, ttl in ttl_map.items():
            self.caches[name] = TTLCache(maxsize=10_000, ttl=ttl)

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Optional[Any]:
        """
        Call the middleware.

        :param handler: The handler function.
        :param event: The Telegram event.
        :param data: Additional data.
        :return: The result of the handler function.
        """
        user: Optional[User] = data.get("event_from_user", None)

        if user is not None:
            # Get the throttling key from data or use the default key
            throttling_key = get_flag(data, "throttling_key", default=self.default_key)
            # Check if the user is already throttled for the given key
            cache = self.caches.get(throttling_key) if throttling_key else None
            if cache is not None and user.id in cache:
                # Delete the message if it exists
                with suppress(Exception):
                    if isinstance(event, Message):
                        await event.delete()
                    else:
                        message = getattr(event, "message", None)
                        if message is not None:
                            await message.delete()
                return None

            if cache is not None:
                cache[user.id] = None

        # Call the handler function with the event and data
        return await handler(event, data)

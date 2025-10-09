from __future__ import annotations

from redis.asyncio import Redis


class SettingsStorage:
    """Storage for bot-wide settings."""

    NAME = "settings"
    GREETING_PREFIX = "greeting:"
    RESOLVED_PREFIX = "resolved_message:"

    def __init__(self, redis: Redis) -> None:
        """Initialize storage with a Redis client."""
        self.redis = redis

    async def _collect_prefixed(self, prefix: str) -> dict[str, str]:
        """Return a mapping filtered by a prefix."""
        async with self.redis.client() as client:
            raw = await client.hgetall(self.NAME)

        result: dict[str, str] = {}
        for key, value in raw.items():
            decoded_key = key.decode() if isinstance(key, bytes) else key
            if not decoded_key.startswith(prefix):
                continue

            language = decoded_key[len(prefix):]
            decoded_value = value.decode() if isinstance(value, bytes) else value
            result[language] = decoded_value

        return result

    async def _get_prefixed_value(self, prefix: str, language: str) -> str | None:
        """Return a stored value for the language if present."""
        async with self.redis.client() as client:
            value = await client.hget(self.NAME, f"{prefix}{language}")

        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else value

    async def _set_prefixed_value(self, prefix: str, language: str, text: str) -> None:
        """Persist a value for the language."""
        async with self.redis.client() as client:
            await client.hset(self.NAME, f"{prefix}{language}", text)

    async def _reset_prefixed_value(self, prefix: str, language: str) -> None:
        """Remove a value for the language if it exists."""
        async with self.redis.client() as client:
            await client.hdel(self.NAME, f"{prefix}{language}")

    async def get_all_greetings(self) -> dict[str, str]:
        """Return greetings overrides indexed by language."""
        return await self._collect_prefixed(self.GREETING_PREFIX)

    async def get_greeting(self, language: str) -> str | None:
        """Return greeting override for the language if present."""
        return await self._get_prefixed_value(self.GREETING_PREFIX, language)

    async def set_greeting(self, language: str, text: str) -> None:
        """Persist greeting override for the language."""
        await self._set_prefixed_value(self.GREETING_PREFIX, language, text)

    async def reset_greeting(self, language: str) -> None:
        """Remove greeting override for the language if it exists."""
        await self._reset_prefixed_value(self.GREETING_PREFIX, language)

    async def get_all_resolved_messages(self) -> dict[str, str]:
        """Return ticket resolution overrides indexed by language."""
        return await self._collect_prefixed(self.RESOLVED_PREFIX)

    async def get_resolved_message(self, language: str) -> str | None:
        """Return ticket resolution override for the language if present."""
        return await self._get_prefixed_value(self.RESOLVED_PREFIX, language)

    async def set_resolved_message(self, language: str, text: str) -> None:
        """Persist ticket resolution override for the language."""
        await self._set_prefixed_value(self.RESOLVED_PREFIX, language, text)

    async def reset_resolved_message(self, language: str) -> None:
        """Remove ticket resolution override for the language if it exists."""
        await self._reset_prefixed_value(self.RESOLVED_PREFIX, language)

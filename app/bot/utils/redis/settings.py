from __future__ import annotations

from redis.asyncio import Redis


class SettingsStorage:
    """Storage for bot-wide settings."""

    NAME = "settings"
    GREETING_PREFIX = "greeting:"

    def __init__(self, redis: Redis) -> None:
        """Initialize storage with a Redis client."""
        self.redis = redis

    async def get_all_greetings(self) -> dict[str, str]:
        """Return greetings overrides indexed by language."""
        async with self.redis.client() as client:
            raw = await client.hgetall(self.NAME)

        result: dict[str, str] = {}
        for key, value in raw.items():
            decoded_key = key.decode() if isinstance(key, bytes) else key
            if not decoded_key.startswith(self.GREETING_PREFIX):
                continue

            language = decoded_key[len(self.GREETING_PREFIX):]
            decoded_value = value.decode() if isinstance(value, bytes) else value
            result[language] = decoded_value

        return result

    async def get_greeting(self, language: str) -> str | None:
        """Return greeting override for the language if present."""
        async with self.redis.client() as client:
            value = await client.hget(self.NAME, f"{self.GREETING_PREFIX}{language}")

        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else value

    async def set_greeting(self, language: str, text: str) -> None:
        """Persist greeting override for the language."""
        async with self.redis.client() as client:
            await client.hset(self.NAME, f"{self.GREETING_PREFIX}{language}", text)

    async def reset_greeting(self, language: str) -> None:
        """Remove greeting override for the language if it exists."""
        async with self.redis.client() as client:
            await client.hdel(self.NAME, f"{self.GREETING_PREFIX}{language}")

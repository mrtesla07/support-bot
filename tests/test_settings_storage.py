import asyncio
from typing import Any

from app.bot.utils.redis.settings import SettingsStorage


class FakeRedisClient:
    def __init__(self, storage: dict[str, dict[str, str]]):
        self._storage = storage

    async def hgetall(self, name: str) -> dict[str, str]:
        return self._storage.get(name, {}).copy()

    async def hget(self, name: str, key: str) -> str | None:
        return self._storage.get(name, {}).get(key)

    async def hset(self, name: str, key: str, value: str) -> None:
        bucket = self._storage.setdefault(name, {})
        bucket[key] = value

    async def hdel(self, name: str, key: str) -> None:
        bucket = self._storage.get(name)
        if bucket and key in bucket:
            del bucket[key]


class FakeRedisContext:
    def __init__(self, storage: dict[str, dict[str, str]]):
        self._storage = storage

    async def __aenter__(self) -> FakeRedisClient:  # type: ignore[override]
        return FakeRedisClient(self._storage)

    async def __aexit__(self, *exc: Any) -> None:  # type: ignore[override]
        return None


class FakeRedis:
    def __init__(self, initial: dict[str, dict[str, str]] | None = None):
        self._storage: dict[str, dict[str, str]] = initial or {}

    def client(self) -> FakeRedisContext:
        return FakeRedisContext(self._storage)


def test_get_all_greetings_filters_only_prefixed_keys() -> None:
    redis = FakeRedis({
        SettingsStorage.NAME: {
            "greeting:en": "Hello!",
            "greeting:ru": "Привет!",
            "unrelated": "should be ignored",
        }
    })
    storage = SettingsStorage(redis)  # type: ignore[arg-type]

    result = asyncio.run(storage.get_all_greetings())

    assert result == {"en": "Hello!", "ru": "Привет!"}


def test_set_get_and_reset_roundtrip() -> None:
    redis = FakeRedis()
    storage = SettingsStorage(redis)  # type: ignore[arg-type]

    assert asyncio.run(storage.get_greeting("en")) is None

    asyncio.run(storage.set_greeting("en", "Hello {full_name}"))
    assert asyncio.run(storage.get_greeting("en")) == "Hello {full_name}"

    asyncio.run(storage.reset_greeting("en"))
    assert asyncio.run(storage.get_greeting("en")) is None


def test_get_all_resolved_filters_only_prefixed_keys() -> None:
    redis = FakeRedis({
        SettingsStorage.NAME: {
            "resolved_message:en": "Thanks!",
            "resolved_message:ru": "Спасибо!",
            "greeting:en": "ignored for resolved",
        }
    })
    storage = SettingsStorage(redis)  # type: ignore[arg-type]

    result = asyncio.run(storage.get_all_resolved_messages())

    assert result == {"en": "Thanks!", "ru": "Спасибо!"}


def test_resolved_message_roundtrip() -> None:
    redis = FakeRedis()
    storage = SettingsStorage(redis)  # type: ignore[arg-type]

    assert asyncio.run(storage.get_resolved_message("en")) is None

    asyncio.run(storage.set_resolved_message("en", "Bye!"))
    assert asyncio.run(storage.get_resolved_message("en")) == "Bye!"

    asyncio.run(storage.reset_resolved_message("en"))
    assert asyncio.run(storage.get_resolved_message("en")) is None

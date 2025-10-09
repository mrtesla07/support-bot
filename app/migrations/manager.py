from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Iterable

from aiogram import Bot
from redis.asyncio import Redis

from app.bot.utils.redis import RedisStorage
from app.config import Config

from . import registry

logger = logging.getLogger(__name__)

MigrationCallback = Callable[["MigrationContext"], Awaitable[None]]


@dataclass(slots=True)
class Migration:
    version: int
    description: str
    callback: MigrationCallback


@dataclass(slots=True)
class MigrationContext:
    config: Config
    bot: Bot
    redis: Redis
    storage: RedisStorage
    throttle_delay: float = 0.05

    async def sleep(self) -> None:
        if self.throttle_delay > 0:
            await asyncio.sleep(self.throttle_delay)


class MigrationManager:
    VERSION_KEY = "support_bot:migration_version"

    def __init__(self, *, config: Config, bot: Bot, redis: Redis) -> None:
        self.config = config
        self.bot = bot
        self.redis = redis
        self.storage = RedisStorage(redis)

    async def _get_current_version(self) -> int:
        value = await self.redis.get(self.VERSION_KEY)
        if value is None:
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    async def _set_current_version(self, version: int) -> None:
        await self.redis.set(self.VERSION_KEY, version)

    async def run_pending(self) -> None:
        current_version = await self._get_current_version()
        pending = [
            migration for migration in self._get_migrations() if migration.version > current_version
        ]
        if not pending:
            logger.info("No migrations required (current version=%s).", current_version)
            return

        context = MigrationContext(
            config=self.config,
            bot=self.bot,
            redis=self.redis,
            storage=self.storage,
        )

        for migration in sorted(pending, key=lambda m: m.version):
            logger.info("Starting migration %s: %s", migration.version, migration.description)
            await migration.callback(context)
            await self._set_current_version(migration.version)
            logger.info("Migration %s completed.", migration.version)

    @staticmethod
    def _get_migrations() -> Iterable[Migration]:
        return registry.MIGRATIONS


async def run_migrations(*, config: Config, bot: Bot, redis: Redis) -> None:
    manager = MigrationManager(config=config, bot=bot, redis=redis)
    await manager.run_pending()

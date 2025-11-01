#!/usr/bin/env python3
"""
Утилита для резервного копирования и восстановления данных Redis,
которые использует support-bot.

Выгружает/загружает:
  - hash "users" (основные данные пользователя);
  - индексы "users_index_*" (сопоставление ID темы → ID пользователя);
  - hash "settings" (настройки приветствий и текста закрытия тикета);
  - hash "faq:items" и список "faq:order" (раздел часто задаваемых вопросов).

Использование:
  python scripts/redis_backup.py backup /path/to/backup.json
  python scripts/redis_backup.py restore /path/to/backup.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from environs import Env
from redis.asyncio import Redis

USERS_HASH = "users"
SETTINGS_HASH = "settings"
FAQ_ITEMS_HASH = "faq:items"
FAQ_ORDER_KEY = "faq:order"
USER_INDEX_PREFIX = f"{USERS_HASH}_index_"


def load_redis_url() -> str:
    env = Env()
    env.read_env()
    host = env.str("REDIS_HOST", "localhost")
    port = env.int("REDIS_PORT", 6379)
    db = env.int("REDIS_DB", 0)
    password = env.str("REDIS_PASSWORD", default=None)

    if password:
        return f"redis://:{password}@{host}:{port}/{db}"
    return f"redis://{host}:{port}/{db}"


async def collect_indexes(redis: Redis) -> Dict[str, Dict[str, str]]:
    result: Dict[str, Dict[str, str]] = {}
    cursor = 0
    pattern = f"{USER_INDEX_PREFIX}*"
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
        if not keys:
            if cursor == 0:
                break
            continue
        for key in keys:
            result[key] = await redis.hgetall(key)
        if cursor == 0:
            break
    return result


async def backup(redis: Redis, target: Path) -> None:
    users_raw = await redis.hgetall(USERS_HASH)
    users: Dict[str, Any] = {
        key: json.loads(value) for key, value in users_raw.items()
    }

    settings = await redis.hgetall(SETTINGS_HASH)
    indexes = await collect_indexes(redis)
    faq_items_raw = await redis.hgetall(FAQ_ITEMS_HASH)
    faq_items: Dict[str, Any] = {
        key: json.loads(value) for key, value in faq_items_raw.items()
    }
    faq_order_raw = await redis.lrange(FAQ_ORDER_KEY, 0, -1)
    faq_order = [
        item.decode() if isinstance(item, bytes) else item for item in faq_order_raw
    ]

    payload = {
        "meta": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": str(target),
        },
        "users": users,
        "indexes": indexes,
        "settings": settings,
        "faq": {
            "items": faq_items,
            "order": faq_order,
        },
    }

    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


async def cleanup_indexes(redis: Redis) -> None:
    cursor = 0
    pattern = f"{USER_INDEX_PREFIX}*"
    keys_to_delete = []
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
        keys_to_delete.extend(keys)
        if cursor == 0:
            break
    for chunk_start in range(0, len(keys_to_delete), 100):
        chunk = keys_to_delete[chunk_start:chunk_start + 100]
        if chunk:
            await redis.delete(*chunk)


async def restore(redis: Redis, source: Path) -> None:
    data = json.loads(source.read_text(encoding="utf-8"))

    users: Dict[str, Any] = data.get("users", {})
    indexes: Dict[str, Dict[str, str]] = data.get("indexes", {})
    settings: Dict[str, str] = data.get("settings", {})
    faq_section: Dict[str, Any] = data.get("faq", {})
    faq_items: Dict[str, Any] = faq_section.get("items", {})
    faq_order: list[str] = faq_section.get("order", [])

    pipeline = redis.pipeline()
    pipeline.delete(USERS_HASH)
    pipeline.delete(SETTINGS_HASH)
    pipeline.delete(FAQ_ITEMS_HASH)
    pipeline.delete(FAQ_ORDER_KEY)
    await cleanup_indexes(redis)
    await pipeline.execute()

    if users:
        pipeline = redis.pipeline()
        for user_id, payload in users.items():
            pipeline.hset(USERS_HASH, user_id, json.dumps(payload, ensure_ascii=False))
        await pipeline.execute()

    if indexes:
        for key, hash_payload in indexes.items():
            if not hash_payload:
                await redis.delete(key)
                continue
            pipe = redis.pipeline()
            pipe.delete(key)
            pipe.hset(key, mapping=hash_payload)
            await pipe.execute()

    if settings:
        await redis.hset(SETTINGS_HASH, mapping=settings)

    if faq_items:
        pipeline = redis.pipeline()
        for item_id, payload in faq_items.items():
            pipeline.hset(FAQ_ITEMS_HASH, item_id, json.dumps(payload, ensure_ascii=False))
        await pipeline.execute()

    await redis.delete(FAQ_ORDER_KEY)
    if faq_order:
        await redis.rpush(FAQ_ORDER_KEY, *faq_order)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Резервное копирование Redis данных support-bot.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup", help="Сделать JSON-бэкап Redis")
    backup_parser.add_argument("output", type=Path, help="Путь к файлу для сохранения")

    restore_parser = subparsers.add_parser("restore", help="Восстановить данные из JSON-бэкапа")
    restore_parser.add_argument("input", type=Path, help="Путь к файлу с бэкапом")

    args = parser.parse_args()

    redis_url = load_redis_url()
    redis = Redis.from_url(redis_url, decode_responses=True)
    try:
        if args.command == "backup":
            await backup(redis, args.output)
            print(f"Бэкап сохранён в {args.output}")
        elif args.command == "restore":
            await restore(redis, args.input)
            print(f"Данные восстановлены из {args.input}")
    finally:
        await redis.close()


if __name__ == "__main__":
    asyncio.run(main())

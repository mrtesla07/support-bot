from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from typing import Any, Iterable
from uuid import uuid4

from redis.asyncio import Redis


@dataclass
class FAQAttachment:
    """Attachment associated with an FAQ item."""

    type: str
    file_id: str
    caption: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FAQAttachment":
        return cls(
            type=payload.get("type", ""),
            file_id=payload.get("file_id", ""),
            caption=payload.get("caption"),
        )


@dataclass
class FAQItem:
    """FAQ entry that can be shown to users."""

    id: str
    title: str
    text: str | None = None
    attachments: list[FAQAttachment] = field(default_factory=list)

    def to_json(self) -> str:
        data = asdict(self)
        data["attachments"] = [asdict(attachment) for attachment in self.attachments]
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_json(cls, payload: str) -> "FAQItem":
        data = json.loads(payload)
        attachments_data: Iterable[dict[str, Any]] = data.get("attachments", [])
        attachments = [FAQAttachment.from_dict(item) for item in attachments_data]
        return cls(
            id=data["id"],
            title=data["title"],
            text=data.get("text"),
            attachments=attachments,
        )


class FAQStorage:
    """Redis-backed storage for frequently asked questions."""

    ITEMS_KEY = "faq:items"
    ORDER_KEY = "faq:order"

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def list_items(self) -> list[FAQItem]:
        """Return FAQ items in stored order."""
        async with self.redis.client() as client:
            raw_ids = await client.lrange(self.ORDER_KEY, 0, -1)

        faq_items: list[FAQItem] = []
        for raw_id in raw_ids:
            item_id = raw_id.decode() if isinstance(raw_id, bytes) else raw_id
            item = await self.get_item(item_id)
            if item is not None:
                faq_items.append(item)

        return faq_items

    async def has_items(self) -> bool:
        """Check whether any FAQ entries exist."""
        async with self.redis.client() as client:
            length = await client.llen(self.ORDER_KEY)
        return length > 0

    async def get_item(self, item_id: str) -> FAQItem | None:
        """Fetch FAQ item by identifier."""
        async with self.redis.client() as client:
            payload = await client.hget(self.ITEMS_KEY, item_id)

        if payload is None:
            return None
        if isinstance(payload, bytes):
            payload = payload.decode()
        return FAQItem.from_json(payload)

    async def add_item(
        self,
        title: str,
        text: str | None,
        attachments: list[FAQAttachment] | None = None,
    ) -> FAQItem:
        """Create a new FAQ entry."""
        item = FAQItem(
            id=str(uuid4()),
            title=title,
            text=text,
            attachments=attachments or [],
        )
        async with self.redis.client() as client:
            await client.hset(self.ITEMS_KEY, item.id, item.to_json())
            await client.rpush(self.ORDER_KEY, item.id)
        return item

    async def update_item(self, item: FAQItem) -> None:
        """Persist changes for an FAQ entry."""
        async with self.redis.client() as client:
            await client.hset(self.ITEMS_KEY, item.id, item.to_json())

    async def rename_item(self, item_id: str, title: str) -> FAQItem | None:
        """Rename an existing FAQ entry."""
        item = await self.get_item(item_id)
        if item is None:
            return None
        item.title = title
        await self.update_item(item)
        return item

    async def update_content(
        self,
        item_id: str,
        *,
        text: str | None,
        attachments: list[FAQAttachment],
    ) -> FAQItem | None:
        """Replace textual content and attachments for an FAQ entry."""
        item = await self.get_item(item_id)
        if item is None:
            return None
        item.text = text
        item.attachments = attachments
        await self.update_item(item)
        return item

    async def delete_item(self, item_id: str) -> None:
        """Remove FAQ entry and its order record."""
        async with self.redis.client() as client:
            await client.hdel(self.ITEMS_KEY, item_id)
            await client.lrem(self.ORDER_KEY, 0, item_id)

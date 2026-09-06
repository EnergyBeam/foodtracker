from __future__ import annotations

import json
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pantry_bot.models import PantryItem, PendingImport, User
from pantry_bot.schemas import ExtractedItem


def normalize_name(value: str) -> str:
    return " ".join(value.strip().lower().split())


class PantryRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    @staticmethod
    async def _ensure_user(session: AsyncSession, user_id: int) -> None:
        if await session.get(User, user_id) is None:
            session.add(User(id=user_id))
            await session.flush()

    @staticmethod
    async def _add_items(session: AsyncSession, user_id: int, items: list[ExtractedItem]) -> None:
        for item in items:
            name = normalize_name(item.name)
            existing = await session.scalar(
                select(PantryItem).where(
                    PantryItem.user_id == user_id,
                    PantryItem.name == name,
                    PantryItem.unit == item.unit,
                )
            )
            if existing:
                existing.quantity += item.quantity
            else:
                session.add(
                    PantryItem(
                        user_id=user_id,
                        name=name,
                        quantity=item.quantity,
                        unit=item.unit,
                    )
                )

    async def ensure_user(self, user_id: int) -> None:
        async with self.sessions.begin() as session:
            await self._ensure_user(session, user_id)

    async def list_items(self, user_id: int) -> list[PantryItem]:
        async with self.sessions() as session:
            result = await session.scalars(
                select(PantryItem).where(PantryItem.user_id == user_id).order_by(PantryItem.name)
            )
            return list(result)

    async def add_items(self, user_id: int, items: list[ExtractedItem]) -> None:
        async with self.sessions.begin() as session:
            await self._ensure_user(session, user_id)
            await self._add_items(session, user_id, items)

    async def consume(self, user_id: int, name: str, quantity: float) -> float | None:
        name = normalize_name(name)
        async with self.sessions.begin() as session:
            item = await session.scalar(
                select(PantryItem).where(PantryItem.user_id == user_id, PantryItem.name == name)
            )
            if item is None:
                return None
            item.quantity -= quantity
            if item.quantity <= 0:
                await session.delete(item)
                return 0
            return item.quantity

    async def create_pending(self, user_id: int, items: list[ExtractedItem]) -> str:
        pending_id = secrets.token_hex(6)
        payload = json.dumps([item.model_dump() for item in items], ensure_ascii=False)
        async with self.sessions.begin() as session:
            await self._ensure_user(session, user_id)
            session.add(PendingImport(id=pending_id, user_id=user_id, payload=payload))
        return pending_id

    async def confirm_pending(self, user_id: int, pending_id: str) -> list[ExtractedItem] | None:
        async with self.sessions.begin() as session:
            pending = await session.get(PendingImport, pending_id)
            if pending is None or pending.user_id != user_id or pending.status != "pending":
                return None
            items = [ExtractedItem.model_validate(item) for item in json.loads(pending.payload)]
            pending.status = "confirmed"
            await self._add_items(session, user_id, items)
            return items

    async def cancel_pending(self, user_id: int, pending_id: str) -> bool:
        async with self.sessions.begin() as session:
            pending = await session.get(PendingImport, pending_id)
            if pending is None or pending.user_id != user_id or pending.status != "pending":
                return False
            pending.status = "cancelled"
            return True

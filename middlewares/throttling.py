"""Anti-spam middleware: Redis orqali tugmalar orasidagi interval va daqiqalik limit."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from redis.asyncio import Redis

from utils import templates

MIN_INTERVAL = 2  # soniya
MAX_PER_MINUTE = 10


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis):
        self.redis = redis
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        uid = user.id
        interval_key = f"throttle:i:{uid}"
        minute_key = f"throttle:m:{uid}"

        # 1) Minimal interval
        if await self.redis.get(interval_key):
            return await self._reject(event)
        await self.redis.set(interval_key, "1", ex=MIN_INTERVAL)

        # 2) Daqiqalik limit
        count = await self.redis.incr(minute_key)
        if count == 1:
            await self.redis.expire(minute_key, 60)
        if count > MAX_PER_MINUTE:
            return await self._reject(event)

        return await handler(event, data)

    async def _reject(self, event: TelegramObject) -> None:
        try:
            if isinstance(event, CallbackQuery):
                await event.answer(templates.THROTTLE, show_alert=False)
            elif isinstance(event, Message):
                await event.answer(templates.THROTTLE)
        except Exception:
            pass
        return None

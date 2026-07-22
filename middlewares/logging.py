"""Oddiy logging middleware — har bir yangilanishni logga yozadi."""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger("shdr_bot")


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        uid = user.id if user else "—"
        if isinstance(event, Message):
            logger.info("msg uid=%s text=%r ct=%s", uid, (event.text or "")[:40], event.content_type)
        elif isinstance(event, CallbackQuery):
            logger.info("cb  uid=%s data=%r", uid, event.data)
        return await handler(event, data)

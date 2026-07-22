"""Auth middleware: har bir yangilanishga xodim obyektini va sessiyani biriktiradi."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database.queries import get_employee_by_tg
from database.session import async_session_maker


class AuthMiddleware(BaseMiddleware):
    """`data['employee']` va `data['session']` ni to'ldiradi.

    Sessiya har bir yangilanish uchun ochiladi va yopiladi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        async with async_session_maker() as session:
            data["session"] = session
            data["employee"] = None
            if user is not None:
                data["employee"] = await get_employee_by_tg(session, user.id)
            return await handler(event, data)

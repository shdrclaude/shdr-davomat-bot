"""SHDR davomat boti — kirish nuqtasi."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from redis.asyncio import Redis

from config import settings
from handlers import (
    admin,
    attendance,
    breaks,
    common,
    registration,
    reports,
    requests,
    setup,
)
from middlewares.auth import AuthMiddleware
from middlewares.logging import LoggingMiddleware
from middlewares.throttling import ThrottlingMiddleware
from services.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("shdr_bot")

# FSM 10 daqiqa harakatsiz qolsa avtomatik tozalanadi
FSM_TTL = 600


async def on_startup(bot: Bot):
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Boshlash / menyu"),
            BotCommand(command="cancel", description="Bekor qilish"),
            BotCommand(command="id", description="Telegram ID"),
        ]
    )
    logger.info("Bot ishga tushdi.")


async def main():
    redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    storage = RedisStorage(redis, state_ttl=FSM_TTL, data_ttl=FSM_TTL)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=None),
    )
    dp = Dispatcher(storage=storage)

    # Middleware'lar (tartib muhim)
    dp.update.outer_middleware(AuthMiddleware())
    dp.message.middleware(ThrottlingMiddleware(redis))
    dp.callback_query.middleware(ThrottlingMiddleware(redis))
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())

    # Routerlar
    dp.include_router(setup.router)
    dp.include_router(common.router)
    dp.include_router(registration.router)
    dp.include_router(attendance.router)
    dp.include_router(breaks.router)
    dp.include_router(requests.router)
    dp.include_router(reports.router)
    dp.include_router(admin.router)

    # Xato handleri
    @dp.errors()
    async def _on_error(event):  # noqa: ANN001
        logger.exception("Xato: %s", event.exception)
        try:
            from utils import templates
            upd = event.update
            if upd.message:
                await upd.message.answer(templates.TECH_ERROR)
            elif upd.callback_query:
                await upd.callback_query.answer(templates.TECH_ERROR, show_alert=True)
        except Exception:
            pass
        if settings.log_chat_id:
            try:
                await bot.send_message(settings.log_chat_id, f"⚠️ Xato:\n{event.exception}")
            except Exception:
                pass
        return True

    scheduler = setup_scheduler(bot)
    scheduler.start()

    await on_startup(bot)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        await redis.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")

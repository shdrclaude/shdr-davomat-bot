"""Xabar yuborish yordamchilari (xodim/admin/guruhga)."""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Branch, Employee
from database.queries import get_branch, list_admins_for_branch

logger = logging.getLogger("shdr_bot")


async def safe_send(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    """Xatolarga chidamli xabar yuborish (bloklangan foydalanuvchini o'tkazib yuboradi)."""
    try:
        await bot.send_message(chat_id, text, reply_markup=reply_markup)
        return True
    except (TelegramForbiddenError, TelegramBadRequest) as e:
        logger.warning("Xabar yuborilmadi chat_id=%s: %s", chat_id, e)
        return False
    except Exception as e:  # noqa: BLE001
        logger.exception("Kutilmagan xato chat_id=%s: %s", chat_id, e)
        return False


async def notify_branch_admins(
    bot: Bot,
    session: AsyncSession,
    branch_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Filial admin guruhiga va shaxsan admin/menejerlarga yuboradi."""
    sent_to: set[int] = set()

    branch: Branch | None = await get_branch(session, branch_id)
    if branch and branch.admin_chat_id:
        if await safe_send(bot, branch.admin_chat_id, text, reply_markup):
            sent_to.add(branch.admin_chat_id)

    admins = await list_admins_for_branch(session, branch_id)
    for adm in admins:
        if adm.telegram_id in sent_to:
            continue
        await safe_send(bot, adm.telegram_id, text, reply_markup)
        sent_to.add(adm.telegram_id)


async def notify_employee(bot: Bot, emp: Employee, text: str, reply_markup=None) -> None:
    await safe_send(bot, emp.telegram_id, text, reply_markup)

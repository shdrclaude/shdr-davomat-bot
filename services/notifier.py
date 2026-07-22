"""Xabar yuborish yordamchilari (xodim/admin/super-admin/nazoratchi/guruhga)."""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import Branch, Employee
from database.queries import get_branch, list_admins_for_branch, list_supervisors

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


async def notify_supervisors(bot: Bot, session: AsyncSession, text: str) -> set[int]:
    """Barcha nazoratchilarga (matn) yuboradi. Yuborilgan id'lar to'plamini qaytaradi."""
    sent: set[int] = set()
    for sup in await list_supervisors(session):
        if await safe_send(bot, sup.telegram_id, text):
            sent.add(sup.telegram_id)
    return sent


async def notify_branch_admins(
    bot: Bot,
    session: AsyncSession,
    branch_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Xabarni quyidagilarga yuboradi:
    - filial admin guruhiga
    - filial admin/menejerlariga
    - super-adminlarga (founder) — filialidan qat'i nazar, tugmalari bilan
    - barcha nazoratchilarga (faqat matn)
    """
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

    # Super-adminlar (founder) — barcha filiallarning bildirishnomalarini tugma bilan oladi
    for sa_id in settings.super_admin_ids:
        if sa_id in sent_to:
            continue
        await safe_send(bot, sa_id, text, reply_markup)
        sent_to.add(sa_id)

    # Nazoratchilar — barcha filiallar, faqat matn
    for sup in await list_supervisors(session):
        if sup.telegram_id in sent_to:
            continue
        await safe_send(bot, sup.telegram_id, text)
        sent_to.add(sup.telegram_id)


async def notify_employee(bot: Bot, emp: Employee, text: str, reply_markup=None) -> None:
    await safe_send(bot, emp.telegram_id, text, reply_markup)

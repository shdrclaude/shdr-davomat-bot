"""Bootstrap: super-admin uchun boshlang'ich sozlash buyruqlari."""
from __future__ import annotations

from datetime import time

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import Branch, Employee, EmployeeStatus, Role
from database.queries import list_branches
from utils.time_helpers import today_local

router = Router(name="setup")


@router.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(
        f"🆔 Sizning Telegram ID: `{message.from_user.id}`\n"
        f"💬 Chat ID: `{message.chat.id}`",
        parse_mode="Markdown",
    )


@router.message(Command("setup"))
async def cmd_setup(message: Message, state: FSMContext, session: AsyncSession, employee: Employee | None):
    """Faqat SUPER_ADMINS ro'yxatidagilar. Boshlang'ich filial va adminni yaratadi."""
    if message.from_user.id not in settings.super_admin_ids:
        await message.answer("⛔ Bu buyruq faqat super-admin uchun.")
        return
    await state.clear()

    branches = await list_branches(session)
    if not branches:
        branch = Branch(
            name="SHDR ASOSIY",
            work_start=time(9, 0),
            work_end=time(18, 0),
            work_days="1,2,3,4,5,6",
            admin_chat_id=message.chat.id,
        )
        session.add(branch)
        await session.commit()
        await session.refresh(branch)
    else:
        branch = branches[0]
        branch.admin_chat_id = message.chat.id
        await session.commit()

    # super-adminni admin sifatida ro'yxatga olish / yangilash
    if employee is None:
        emp = Employee(
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name or "Super Admin",
            username=message.from_user.username,
            branch_id=branch.id,
            position="Administrator",
            role=Role.admin,
            status=EmployeeStatus.faol,
        )
        session.add(emp)
    else:
        employee.role = Role.admin
        employee.status = EmployeeStatus.faol
        employee.branch_id = branch.id
    await session.commit()

    await message.answer(
        f"✅ Sozlash tayyor.\n\n"
        f"🏢 Filial: {branch.name}\n"
        f"💬 Admin guruh: shu chat ({message.chat.id})\n"
        f"👤 Siz admin sifatida qo'shildingiz.\n\n"
        f"Endi filial nomini o'zgartirish uchun: /branch_name Yangi nom\n"
        f"Ish vaqtini o'zgartirish uchun: /work_time 09:00 18:00"
    )


@router.message(Command("branch_name"))
async def cmd_branch_name(message: Message, session: AsyncSession, employee: Employee | None):
    if not employee or employee.role != Role.admin:
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Foydalanish: /branch_name SHDR QO'QON")
        return
    branch = employee.branch
    if branch:
        branch.name = parts[1].strip()
        await session.commit()
        await message.answer(f"✅ Filial nomi yangilandi: {branch.name}")


@router.message(Command("work_time"))
async def cmd_work_time(message: Message, session: AsyncSession, employee: Employee | None):
    if not employee or employee.role != Role.admin:
        return
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer("Foydalanish: /work_time 09:00 18:00")
        return
    try:
        sh, sm = map(int, parts[1].split(":"))
        eh, em = map(int, parts[2].split(":"))
        branch = employee.branch
        branch.work_start = time(sh, sm)
        branch.work_end = time(eh, em)
        await session.commit()
        await message.answer(f"✅ Ish vaqti: {parts[1]} — {parts[2]}")
    except (ValueError, AttributeError):
        await message.answer("❌ Noto'g'ri format. Masalan: /work_time 09:00 18:00")


@router.message(Command("newbranch"))
async def cmd_newbranch(message: Message, session: AsyncSession, employee: Employee | None):
    """Super-admin yangi filial qo'shadi: /newbranch SHDR TOSHKENT"""
    if message.from_user.id not in settings.super_admin_ids:
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Foydalanish: /newbranch SHDR TOSHKENT")
        return
    branch = Branch(name=parts[1].strip(), work_start=time(9, 0), work_end=time(18, 0),
                    work_days="1,2,3,4,5,6")
    session.add(branch)
    await session.commit()
    await message.answer(f"✅ Yangi filial qo'shildi: {branch.name}\nID: {branch.id}")

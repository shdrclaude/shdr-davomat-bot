"""Xodim hisoboti (📊 Hisobotim)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Employee, EmployeeStatus
from keyboards import user_kb
from services.report_builder import employee_month_stats
from utils import templates
from utils.time_helpers import today_local

router = Router(name="reports")


@router.message(F.text == "📊 Hisobotim")
async def my_report(message: Message, session: AsyncSession, employee: Employee | None):
    if not employee or employee.status != EmployeeStatus.faol:
        return
    day = today_local()
    stats = await employee_month_stats(session, employee, day.year, day.month)
    name = employee.full_name.split()[0] if employee.full_name else employee.full_name
    await message.answer(
        templates.my_report(name, stats["month_label"], stats),
        reply_markup=user_kb.report_nav_kb(),
    )


@router.callback_query(F.data == "rep_prev")
async def prev_month(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not employee:
        await call.answer()
        return
    day = today_local()
    year, month = (day.year, day.month - 1) if day.month > 1 else (day.year - 1, 12)
    stats = await employee_month_stats(session, employee, year, month)
    name = employee.full_name.split()[0] if employee.full_name else employee.full_name
    await call.message.answer(templates.my_report(name, stats["month_label"], stats))
    await call.answer()


@router.callback_query(F.data == "rep_pick")
async def pick_month(call: CallbackQuery):
    await call.answer("Sana tanlash tez orada qo'shiladi.", show_alert=True)

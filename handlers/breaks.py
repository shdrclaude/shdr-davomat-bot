"""Chiqib ketyapman / Qaytdim."""
from __future__ import annotations

from datetime import timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Employee, EmployeeStatus
from database.queries import (
    close_break,
    count_breaks_today,
    create_break,
    get_open_break,
    get_today_attendance,
    log_action,
)
from handlers.common import refresh_menu
from handlers.states import BreakOut
from keyboards import user_kb
from locales import uz
from services.notifier import notify_branch_admins
from utils import templates
from utils.menu import is_work_time_over
from utils.time_helpers import fmt_time, minutes_between, now_local, today_local
from utils.validators import validate_reason

router = Router(name="breaks")

BREAK_LIMIT_PER_DAY = 3


def _active(emp: Employee | None) -> bool:
    return emp is not None and emp.status == EmployeeStatus.faol


@router.message(F.text == "🚶 Chiqib ketyapman")
async def break_start(message: Message, state: FSMContext, session: AsyncSession, employee: Employee):
    if not _active(employee):
        return
    day = today_local()
    att = await get_today_attendance(session, employee.id, day)
    if not att or not att.check_in or att.check_out:
        await message.answer("ℹ️ Buning uchun avval ishni boshlashingiz kerak.")
        return

    if is_work_time_over(employee):
        await message.answer(templates.BREAK_WORK_ENDED)
        return

    if await get_open_break(session, employee.id, day):
        await message.answer("ℹ️ Siz allaqachon tashqaridasiz. Qaytganingizda tugmani bosing.")
        return

    count = await count_breaks_today(session, employee.id, day)
    if count >= BREAK_LIMIT_PER_DAY:
        await message.answer(templates.BREAK_LIMIT)
        await notify_branch_admins(
            message.bot, session, employee.branch_id,
            templates.admin_break_limit_hit(employee.full_name, employee.branch.name if employee.branch else "—"),
        )
        await log_action(session, employee.id, "break_limit", {})
        return

    await state.update_data(attempts=0)
    await state.set_state(BreakOut.reason)
    await message.answer(templates.BREAK_ASK_WHERE, reply_markup=user_kb.break_reason_kb())


@router.callback_query(BreakOut.reason, F.data.startswith("brr:"))
async def break_reason(call: CallbackQuery, state: FSMContext):
    code = call.data.split(":")[1]
    if code == "other":
        await state.set_state(BreakOut.reason_text)
        await call.message.edit_text("✍️ Qayerga chiqayotganingizni yozing:")
        await call.answer()
        return
    await state.update_data(reason_code=code, reason_text=None)
    await state.set_state(BreakOut.duration)
    await call.message.edit_text(templates.BREAK_ASK_WHEN, reply_markup=user_kb.break_duration_kb())
    await call.answer()


@router.message(BreakOut.reason_text, F.text)
async def break_reason_text(message: Message, state: FSMContext, session: AsyncSession, employee: Employee):
    ok, err = validate_reason(message.text)
    if not ok:
        data = await state.get_data()
        attempts = data.get("attempts", 0) + 1
        await state.update_data(attempts=attempts)
        if attempts >= 3:
            await message.answer(templates.REASON_TOO_MANY,
                                 reply_markup=user_kb.ready_reasons_kb(uz.BREAK_REASONS, "brr"))
            await state.set_state(BreakOut.reason)
            await log_action(session, employee.id, "reason_abuse", {"ctx": "break"})
            return
        await message.answer(err)
        return
    await state.update_data(reason_code="other", reason_text=message.text.strip())
    await state.set_state(BreakOut.duration)
    await message.answer(templates.BREAK_ASK_WHEN, reply_markup=user_kb.break_duration_kb())


@router.callback_query(BreakOut.duration, F.data.startswith("brd:"))
async def break_duration(call: CallbackQuery, state: FSMContext):
    code = call.data.split(":")[1]
    _label, minutes = uz.BREAK_DURATIONS[code]
    back = now_local() + timedelta(minutes=minutes)
    await state.update_data(minutes=minutes, back_time=back.isoformat())
    data = await state.get_data()
    reason = uz.reason_label(uz.BREAK_REASONS, data["reason_code"], data.get("reason_text"))
    await state.set_state(BreakOut.confirm)
    await call.message.edit_text(
        templates.break_preview(reason, minutes, back),
        reply_markup=user_kb.confirm_break_kb(),
    )
    await call.answer()


@router.callback_query(BreakOut.confirm, F.data == "edit")
async def break_edit(call: CallbackQuery, state: FSMContext):
    await state.set_state(BreakOut.reason)
    await state.update_data(attempts=0)
    await call.message.edit_text(templates.BREAK_ASK_WHERE, reply_markup=user_kb.break_reason_kb())
    await call.answer()


@router.callback_query(BreakOut.confirm, F.data == "send")
async def break_confirm(call: CallbackQuery, state: FSMContext, session: AsyncSession, employee: Employee):
    data = await state.get_data()
    now = now_local()
    day = today_local()
    br = await create_break(
        session,
        emp_id=employee.id,
        day=day,
        out_time=now,
        reason_code=data["reason_code"],
        reason_text=data.get("reason_text"),
        expected_minutes=data["minutes"],
    )
    await log_action(session, employee.id, "break_out", {"min": data["minutes"]})
    reason = uz.reason_label(uz.BREAK_REASONS, data["reason_code"], data.get("reason_text"))
    from datetime import datetime
    back = datetime.fromisoformat(data["back_time"])
    await state.clear()
    await call.message.edit_text(templates.break_recorded(now, back, reason))
    await call.answer()
    await refresh_menu(call.message, session, employee)


# ==================== QAYTDIM ====================
@router.message(F.text == "↩️ Qaytdim")
async def qaytdim(message: Message, state: FSMContext, session: AsyncSession, employee: Employee):
    if not _active(employee):
        return
    day = today_local()
    br = await get_open_break(session, employee.id, day)
    if not br:
        await message.answer("ℹ️ Ochiq chiqish topilmadi.")
        return
    now = now_local()
    duration = minutes_between(br.out_time, now)
    expected = br.expected_minutes or 0
    is_overdue = duration > expected
    await close_break(session, br, now, duration, is_overdue)
    await log_action(session, employee.id, "break_back", {"dur": duration, "overdue": is_overdue})
    count = await count_breaks_today(session, employee.id, day)
    await message.answer(templates.break_return(now, duration, expected, count))
    await refresh_menu(message, session, employee)

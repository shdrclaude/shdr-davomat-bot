"""Keldim / Ketdim (video-doira bilan davomat)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Employee, EmployeeStatus
from database.queries import (
    create_check_in,
    get_today_attendance,
    log_action,
    set_check_out,
    sum_break_minutes,
)
from handlers.common import refresh_menu, show_menu
from handlers.states import CheckIn, CheckOut
from keyboards import user_kb
from locales import uz
from utils import templates
from utils.menu import is_work_time_over
from utils.time_helpers import (
    combine_local,
    fmt_time,
    is_workday,
    minutes_between,
    now_local,
    today_local,
)
from utils.validators import validate_reason

router = Router(name="attendance")

MIN_VIDEO_SECONDS = 2


def _active(emp: Employee | None) -> bool:
    return emp is not None and emp.status == EmployeeStatus.faol


# ==================== KELDIM ====================
@router.message(F.text == "✅ Keldim")
async def keldim(message: Message, state: FSMContext, session: AsyncSession, employee: Employee):
    if not _active(employee):
        return
    day = today_local()
    branch = employee.branch

    if branch and not is_workday(day, branch.work_days):
        await message.answer(templates.CHECKIN_DAYOFF)
        return

    att = await get_today_attendance(session, employee.id, day)
    if att and att.check_in:
        await message.answer(templates.CHECKIN_ALREADY.format(time=fmt_time(att.check_in)))
        return

    await state.set_state(CheckIn.video)
    await message.answer(templates.CHECKIN_ASK_VIDEO, reply_markup=user_kb.cancel_kb())


@router.message(CheckIn.video, F.video_note)
async def keldim_video(message: Message, state: FSMContext, session: AsyncSession, employee: Employee):
    if message.video_note.duration < MIN_VIDEO_SECONDS:
        await message.answer(templates.CHECKIN_TOO_SHORT)
        return

    now = now_local()
    day = today_local()
    branch = employee.branch

    is_late = False
    late_minutes = 0
    start_t = employee.work_start or (branch.work_start if branch else None)
    if start_t:
        start_dt = combine_local(day, start_t)
        if now > start_dt:
            is_late = True
            late_minutes = minutes_between(start_dt, now)

    att = await create_check_in(
        session,
        emp_id=employee.id,
        day=day,
        check_in=now,
        video_id=message.video_note.file_id,
        is_late=is_late,
        late_minutes=late_minutes,
    )
    await log_action(session, employee.id, "check_in", {"late": is_late, "min": late_minutes})

    branch_name = branch.name if branch else "—"
    if is_late:
        await state.update_data(attempts=0)
        await state.set_state(CheckIn.late_reason)
        await message.answer(
            templates.checkin_late(employee.full_name.split()[0], now, late_minutes, branch_name),
            reply_markup=user_kb.late_arrival_reason_kb(),
        )
    else:
        await state.clear()
        await message.answer(
            templates.checkin_success(employee.full_name.split()[0], now, branch_name)
        )
        await refresh_menu(message, session, employee)


@router.message(CheckIn.video)
async def keldim_not_video(message: Message):
    await message.answer(templates.CHECKIN_NOT_VIDEO)


@router.callback_query(CheckIn.late_reason, F.data.startswith("lar:"))
async def keldim_late_reason(call: CallbackQuery, state: FSMContext, session: AsyncSession, employee: Employee):
    code = call.data.split(":")[1]
    if code == "other":
        await state.set_state(CheckIn.late_reason_text)
        await call.message.edit_text("✍️ Kechikish sababini yozing:")
        await call.answer()
        return
    await _finish_late_reason(call.message, state, session, employee, code, None)
    await call.answer()


@router.message(CheckIn.late_reason_text, F.text)
async def keldim_late_reason_text(message: Message, state: FSMContext, session: AsyncSession, employee: Employee):
    ok, err = validate_reason(message.text)
    if not ok:
        data = await state.get_data()
        attempts = data.get("attempts", 0) + 1
        await state.update_data(attempts=attempts)
        if attempts >= 3:
            await message.answer(templates.REASON_TOO_MANY,
                                 reply_markup=user_kb.ready_reasons_kb(uz.LATE_ARRIVAL_REASONS, "lar"))
            await state.set_state(CheckIn.late_reason)
            await log_action(session, employee.id, "reason_abuse", {"ctx": "checkin"})
            return
        await message.answer(err)
        return
    await _finish_late_reason(message, state, session, employee, "other", message.text.strip())


async def _finish_late_reason(msg_obj, state, session, employee, code, text):
    await log_action(session, employee.id, "late_reason", {"code": code})
    await state.clear()
    await msg_obj.answer("✅ Kechikish sababi qabul qilindi. Rahmat.")
    await refresh_menu(msg_obj, session, employee)


# ==================== KETDIM ====================
@router.message(F.text == "🚪 Ketdim")
async def ketdim(message: Message, state: FSMContext, session: AsyncSession, employee: Employee):
    if not _active(employee):
        return
    day = today_local()
    att = await get_today_attendance(session, employee.id, day)
    if not att or not att.check_in:
        await message.answer(templates.CHECKOUT_NO_CHECKIN)
        return
    if att.check_out:
        await message.answer("ℹ️ Siz bugun allaqachon ketgansiz.")
        return
    await state.set_state(CheckOut.video)
    await message.answer(templates.CHECKOUT_ASK_VIDEO, reply_markup=user_kb.cancel_kb())


@router.message(CheckOut.video, F.video_note)
async def ketdim_video(message: Message, state: FSMContext, session: AsyncSession, employee: Employee):
    if message.video_note.duration < MIN_VIDEO_SECONDS:
        await message.answer(templates.CHECKIN_TOO_SHORT)
        return
    now = now_local()
    day = today_local()
    att = await get_today_attendance(session, employee.id, day)
    if not att:
        await state.clear()
        await message.answer(templates.CHECKOUT_NO_CHECKIN)
        return

    break_min = await sum_break_minutes(session, employee.id, day)
    total = minutes_between(att.check_in, now)
    worked = max(0, total - break_min)

    await set_check_out(session, att, now, message.video_note.file_id, worked, break_min)
    await log_action(session, employee.id, "check_out", {"worked": worked})

    # chiqishlar soni
    from database.queries import count_breaks_today
    bc = await count_breaks_today(session, employee.id, day)

    await state.clear()
    await message.answer(
        templates.checkout_summary(employee.full_name.split()[0], now, worked, bc, break_min)
    )
    await refresh_menu(message, session, employee)


@router.message(CheckOut.video)
async def ketdim_not_video(message: Message):
    await message.answer(templates.CHECKIN_NOT_VIDEO)

"""Kech qolaman va Dam olish so'rovlari (kalendar, tugmalar, tasdiqlash)."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Employee, EmployeeStatus, RequestType
from database.queries import (
    count_pending_late_today,
    count_pending_vacation_month,
    create_request,
    find_recent_duplicate,
    get_last_pending_late,
    log_action,
)
from handlers.common import refresh_menu
from handlers.states import LateRequest, Vacation
from keyboards import admin_kb, user_kb
from keyboards.calendar_kb import SimpleCalendar, SimpleCalendarCallback, get_calendar
from locales import uz
from services.notifier import notify_branch_admins
from utils import templates
from utils.time_helpers import (
    combine_local,
    fmt_date,
    fmt_duration,
    fmt_time,
    humanize_relative_day,
    month_start,
    now_local,
    today_local,
)
from utils.validators import validate_reason

router = Router(name="requests")


def _active(emp: Employee | None) -> bool:
    return emp is not None and emp.status == EmployeeStatus.faol


def _lateness_text(branch, target_time: time) -> str:
    if not branch:
        return "kech"
    start = combine_local(today_local(), branch.work_start)
    tgt = combine_local(today_local(), target_time)
    diff = int((tgt - start).total_seconds() // 60)
    if diff <= 0:
        return "o'z vaqtida"
    return f"{fmt_duration(diff)} kech"


# ==================== KECH QOLAMAN ====================
@router.message(F.text.in_({"🕐 Kech qolaman", "🕐 Ertaga kech qolaman"}))
async def late_start(message: Message, state: FSMContext, session: AsyncSession, employee: Employee):
    if not _active(employee):
        return
    day = today_local()

    # Limit 1/kun
    if await count_pending_late_today(session, employee.id, day) >= 1:
        req = await get_last_pending_late(session, employee.id, day)
        if req:
            reason = uz.reason_label(uz.LATE_REQUEST_REASONS, req.reason_code, req.reason_text)
            created = req.created_at
            await message.answer(
                templates.late_already(fmt_time(created), req.target_date, req.expected_time, reason),
                reply_markup=user_kb.existing_request_kb(),
            )
            return

    await state.clear()
    await state.update_data(attempts=0)
    await state.set_state(LateRequest.date)
    tomorrow = day + timedelta(days=1)
    day_after = day + timedelta(days=2)
    await message.answer(
        templates.LATE_ASK_DATE,
        reply_markup=user_kb.date_choice_kb(
            f"Ertaga — {fmt_date(tomorrow)}",
            f"Indinga — {fmt_date(day_after)}",
        ),
    )


@router.callback_query(LateRequest.date, F.data.startswith("ldate:"))
async def late_date(call: CallbackQuery, state: FSMContext):
    choice = call.data.split(":")[1]
    if choice == "custom":
        await state.set_state(LateRequest.calendar)
        await call.message.edit_text("📆 Sanani tanlang:", reply_markup=await (await get_calendar()).start_calendar())
        await call.answer()
        return
    target = today_local() + timedelta(days=int(choice))
    await state.update_data(target_date=target.isoformat())
    await state.set_state(LateRequest.time)
    await call.message.edit_text(templates.LATE_ASK_TIME, reply_markup=user_kb.arrival_time_kb())
    await call.answer()


@router.callback_query(LateRequest.calendar, SimpleCalendarCallback.filter())
async def late_calendar(call: CallbackQuery, callback_data, state: FSMContext):
    cal = await get_calendar()
    selected, chosen = await cal.process_selection(call, callback_data)
    if not selected:
        return
    target = chosen.date()
    if target < today_local():
        await call.answer("O'tgan sanani tanlab bo'lmaydi", show_alert=True)
        return
    await state.update_data(target_date=target.isoformat())
    await state.set_state(LateRequest.time)
    await call.message.answer(templates.LATE_ASK_TIME, reply_markup=user_kb.arrival_time_kb())


@router.callback_query(LateRequest.time, F.data.startswith("latt:"))
async def late_time(call: CallbackQuery, state: FSMContext):
    val = call.data.split(":", 1)[1]
    if val == "custom":
        await state.set_state(LateRequest.time_custom)
        await call.message.edit_text("🕐 Kelish vaqtini yozing (masalan: 10:15):")
        await call.answer()
        return
    await state.update_data(expected_time=val)
    await state.set_state(LateRequest.reason)
    await call.message.edit_text(templates.LATE_ASK_REASON, reply_markup=user_kb.late_request_reason_kb())
    await call.answer()


@router.message(LateRequest.time_custom, F.text)
async def late_time_custom(message: Message, state: FSMContext):
    txt = message.text.strip()
    try:
        h, m = txt.split(":")
        t = time(int(h), int(m))
    except (ValueError, TypeError):
        await message.answer("❌ Noto'g'ri format. Masalan: 10:15")
        return
    await state.update_data(expected_time=t.strftime("%H:%M"))
    await state.set_state(LateRequest.reason)
    await message.answer(templates.LATE_ASK_REASON, reply_markup=user_kb.late_request_reason_kb())


@router.callback_query(LateRequest.reason, F.data.startswith("lrr:"))
async def late_reason(call: CallbackQuery, state: FSMContext):
    code = call.data.split(":")[1]
    if code == "other":
        await state.set_state(LateRequest.reason_text)
        await call.message.edit_text("✍️ Sababingizni yozing:")
        await call.answer()
        return
    await state.update_data(reason_code=code, reason_text=None)
    await _late_preview(call.message, state, edit=True)
    await call.answer()


@router.message(LateRequest.reason_text, F.text)
async def late_reason_text(message: Message, state: FSMContext, session: AsyncSession, employee: Employee):
    ok, err = validate_reason(message.text)
    if not ok:
        data = await state.get_data()
        attempts = data.get("attempts", 0) + 1
        await state.update_data(attempts=attempts)
        if attempts >= 3:
            await message.answer(templates.REASON_TOO_MANY,
                                 reply_markup=user_kb.ready_reasons_kb(uz.LATE_REQUEST_REASONS, "lrr"))
            await state.set_state(LateRequest.reason)
            await log_action(session, employee.id, "reason_abuse", {"ctx": "late_req"})
            return
        await message.answer(err)
        return
    await state.update_data(reason_code="other", reason_text=message.text.strip())
    await _late_preview(message, state, edit=False)


async def _late_preview(msg_obj, state: FSMContext, edit: bool):
    data = await state.get_data()
    from datetime import date as _date
    target = _date.fromisoformat(data["target_date"])
    h, m = data["expected_time"].split(":")
    t = time(int(h), int(m))
    reason = uz.reason_label(uz.LATE_REQUEST_REASONS, data["reason_code"], data.get("reason_text"))
    # branch lateness — msg_obj.bot yo'q, shuning uchun oddiy hisob
    late_txt = data.get("late_txt", "belgilangan vaqtdan kech")
    text = templates.late_preview(target, t, late_txt, reason)
    await state.set_state(LateRequest.confirm)
    if edit:
        await msg_obj.edit_text(text, reply_markup=user_kb.confirm_send_kb())
    else:
        await msg_obj.answer(text, reply_markup=user_kb.confirm_send_kb())


@router.callback_query(LateRequest.confirm, F.data == "edit")
async def late_edit(call: CallbackQuery, state: FSMContext):
    await state.set_state(LateRequest.time)
    await call.message.edit_text(templates.LATE_ASK_TIME, reply_markup=user_kb.arrival_time_kb())
    await call.answer()


@router.callback_query(LateRequest.confirm, F.data == "send")
async def late_send(call: CallbackQuery, state: FSMContext, session: AsyncSession, employee: Employee):
    data = await state.get_data()
    from datetime import date as _date
    target = _date.fromisoformat(data["target_date"])
    h, m = data["expected_time"].split(":")
    t = time(int(h), int(m))

    # 5 daqiqalik takror nazorati
    dup = await find_recent_duplicate(
        session, employee.id, RequestType.kech_qolish, datetime.utcnow() - timedelta(minutes=5)
    )
    if dup:
        await call.answer("Bu so'rovni yaqinda yuborgansiz", show_alert=True)
        await state.clear()
        return

    req = await create_request(
        session, employee.id, RequestType.kech_qolish, target, t,
        data["reason_code"], data.get("reason_text"),
    )
    await log_action(session, employee.id, "late_request", {"req_id": req.id})
    await state.clear()
    await call.message.edit_text(templates.REQUEST_SENT)
    await call.answer()

    reason = uz.reason_label(uz.LATE_REQUEST_REASONS, req.reason_code, req.reason_text)
    late_txt = _lateness_text(employee.branch, t)
    admin_text = (
        "🕐 KECH QOLISH SO'ROVI\n\n"
        f"👤 {employee.full_name}\n"
        f"🏢 {employee.branch.name if employee.branch else '—'} — {employee.position or '—'}\n"
        f"📅 {fmt_date(target)}\n"
        f"⏰ Kelish: {fmt_time(t)} ({late_txt})\n"
        f"📝 Sabab: {reason}"
    )
    await notify_branch_admins(
        call.bot, session, employee.branch_id, admin_text,
        reply_markup=admin_kb.review_request_kb(req.id),
    )
    await refresh_menu(call.message, session, employee)


# ==================== DAM OLISH ====================
@router.message(F.text == "🏖 Dam olish so'rash")
async def vacation_start(message: Message, state: FSMContext, session: AsyncSession, employee: Employee):
    if not _active(employee):
        return
    if await count_pending_vacation_month(session, employee.id, month_start(today_local())) >= 3:
        await message.answer("⛔ Oylik limit tugadi (3 ta kutilayotgan so'rov). Rahbar javobini kuting.")
        return
    await state.clear()
    await state.update_data(attempts=0)
    await state.set_state(Vacation.vtype)
    await message.answer(templates.VACATION_ASK_TYPE, reply_markup=user_kb.vacation_type_kb())


@router.callback_query(Vacation.vtype, F.data.startswith("vt:"))
async def vacation_type(call: CallbackQuery, state: FSMContext):
    vtype = call.data.split(":")[1]
    await state.update_data(vtype=vtype)
    await state.set_state(Vacation.calendar)
    await call.message.edit_text("📆 Sanani tanlang:", reply_markup=await (await get_calendar()).start_calendar())
    await call.answer()


@router.callback_query(Vacation.calendar, SimpleCalendarCallback.filter())
async def vacation_calendar(call: CallbackQuery, callback_data, state: FSMContext):
    cal = await get_calendar()
    selected, chosen = await cal.process_selection(call, callback_data)
    if not selected:
        return
    d = chosen.date()
    if d < today_local():
        await call.answer("O'tgan sanani tanlab bo'lmaydi", show_alert=True)
        return
    data = await state.get_data()
    await state.update_data(target_date=d.isoformat())
    if data.get("vtype") == "multi_day":
        await state.set_state(Vacation.end_calendar)
        await call.message.answer("📆 Tugash sanasini tanlang:", reply_markup=await (await get_calendar()).start_calendar())
        return
    await state.set_state(Vacation.reason)
    await call.message.answer(templates.LATE_ASK_REASON, reply_markup=user_kb.vacation_reason_kb())


@router.callback_query(Vacation.end_calendar, SimpleCalendarCallback.filter())
async def vacation_end_calendar(call: CallbackQuery, callback_data, state: FSMContext):
    cal = await get_calendar()
    selected, chosen = await cal.process_selection(call, callback_data)
    if not selected:
        return
    end = chosen.date()
    data = await state.get_data()
    from datetime import date as _date
    start = _date.fromisoformat(data["target_date"])
    if end < start:
        await call.answer("Tugash sanasi boshlanishdan oldin bo'lmaydi", show_alert=True)
        return
    await state.update_data(end_date=end.isoformat())
    await state.set_state(Vacation.reason)
    await call.message.answer(templates.LATE_ASK_REASON, reply_markup=user_kb.vacation_reason_kb())


@router.callback_query(Vacation.reason, F.data.startswith("vrr:"))
async def vacation_reason(call: CallbackQuery, state: FSMContext):
    code = call.data.split(":")[1]
    if code == "other":
        await state.set_state(Vacation.reason_text)
        await call.message.edit_text("✍️ Sababingizni yozing:")
        await call.answer()
        return
    await state.update_data(reason_code=code, reason_text=None)
    await _vacation_preview(call.message, state, edit=True)
    await call.answer()


@router.message(Vacation.reason_text, F.text)
async def vacation_reason_text(message: Message, state: FSMContext, session: AsyncSession, employee: Employee):
    ok, err = validate_reason(message.text)
    if not ok:
        data = await state.get_data()
        attempts = data.get("attempts", 0) + 1
        await state.update_data(attempts=attempts)
        if attempts >= 3:
            await message.answer(templates.REASON_TOO_MANY,
                                 reply_markup=user_kb.ready_reasons_kb(uz.VACATION_REASONS, "vrr"))
            await state.set_state(Vacation.reason)
            await log_action(session, employee.id, "reason_abuse", {"ctx": "vacation"})
            return
        await message.answer(err)
        return
    await state.update_data(reason_code="other", reason_text=message.text.strip())
    await _vacation_preview(message, state, edit=False)


async def _vacation_preview(msg_obj, state: FSMContext, edit: bool):
    data = await state.get_data()
    from datetime import date as _date
    start = _date.fromisoformat(data["target_date"])
    end = _date.fromisoformat(data["end_date"]) if data.get("end_date") else None
    vtype_lbl = uz.VACATION_TYPES.get(data["vtype"], "")
    reason = uz.reason_label(uz.VACATION_REASONS, data["reason_code"], data.get("reason_text"))
    date_line = fmt_date(start) if not end else f"{fmt_date(start)} — {fmt_date(end)}"
    text = (
        "📋 So'rovingizni tekshiring:\n\n"
        f"🏖 Turi: {vtype_lbl}\n"
        f"📅 Sana: {date_line}\n"
        f"📝 Sabab: {reason}"
    )
    await state.set_state(Vacation.confirm)
    if edit:
        await msg_obj.edit_text(text, reply_markup=user_kb.confirm_send_kb())
    else:
        await msg_obj.answer(text, reply_markup=user_kb.confirm_send_kb())


@router.callback_query(Vacation.confirm, F.data == "edit")
async def vacation_edit(call: CallbackQuery, state: FSMContext):
    await state.set_state(Vacation.vtype)
    await call.message.edit_text(templates.VACATION_ASK_TYPE, reply_markup=user_kb.vacation_type_kb())
    await call.answer()


@router.callback_query(Vacation.confirm, F.data == "send")
async def vacation_send(call: CallbackQuery, state: FSMContext, session: AsyncSession, employee: Employee):
    data = await state.get_data()
    from datetime import date as _date
    start = _date.fromisoformat(data["target_date"])
    end = _date.fromisoformat(data["end_date"]) if data.get("end_date") else None

    dup = await find_recent_duplicate(
        session, employee.id, RequestType.dam_olish, datetime.utcnow() - timedelta(minutes=5)
    )
    if dup:
        await call.answer("Bu so'rovni yaqinda yuborgansiz", show_alert=True)
        await state.clear()
        return

    req = await create_request(
        session, employee.id, RequestType.dam_olish, start, None,
        data["reason_code"], data.get("reason_text"), end_date=end,
    )
    await log_action(session, employee.id, "vacation_request", {"req_id": req.id})
    await state.clear()
    await call.message.edit_text(templates.REQUEST_SENT)
    await call.answer()

    reason = uz.reason_label(uz.VACATION_REASONS, req.reason_code, req.reason_text)
    vtype_lbl = uz.VACATION_TYPES.get(data["vtype"], "")
    date_line = fmt_date(start) if not end else f"{fmt_date(start)} — {fmt_date(end)}"
    admin_text = (
        "🏖 DAM OLISH SO'ROVI\n\n"
        f"👤 {employee.full_name}\n"
        f"🏢 {employee.branch.name if employee.branch else '—'} — {employee.position or '—'}\n"
        f"🏖 Turi: {vtype_lbl}\n"
        f"📅 {date_line}\n"
        f"📝 Sabab: {reason}"
    )
    await notify_branch_admins(
        call.bot, session, employee.branch_id, admin_text,
        reply_markup=admin_kb.review_request_kb(req.id),
    )
    await refresh_menu(call.message, session, employee)


# ==================== MAVJUD SO'ROVNI BEKOR QILISH ====================
@router.callback_query(F.data == "req_delete")
async def req_delete(call: CallbackQuery, session: AsyncSession, employee: Employee):
    from database.models import RequestStatus
    from database.queries import get_last_pending_late
    req = await get_last_pending_late(session, employee.id, today_local())
    if req and req.status == RequestStatus.kutilmoqda:
        req.status = RequestStatus.bekor_qilindi
        await session.commit()
        await call.message.edit_text("🗑 So'rov bekor qilindi.")
    await call.answer()


@router.callback_query(F.data == "req_edit")
async def req_edit(call: CallbackQuery, state: FSMContext):
    await call.answer("Avvalgi so'rovni bekor qilib, yangi so'rov yuboring.", show_alert=True)

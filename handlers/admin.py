"""Admin/menejer tarafi: xodim tasdiqlash, so'rovlarga javob, hisobotlar.

Admin funksiyalari asosiy klaviaturada (reply keyboard) tugmalar sifatida
chiqadi. Har bir amal ham reply-tugma (message), ham eski inline (callback)
orqali ishlaydi — logika umumiy yordamchi funksiyalarda.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import (
    Attendance,
    Break,
    Employee,
    EmployeeStatus,
    Request,
    RequestStatus,
    RequestType,
    Role,
)
from database.queries import (
    approve_employee,
    get_employee_by_id,
    get_request,
    list_branch_employees,
    list_pending_requests,
    log_action,
    reject_employee,
    resolve_request,
)
from handlers.states import AdminReview
from keyboards import admin_kb
from locales import uz
from services import excel_export
from services.notifier import notify_employee
from services.report_builder import today_branch_report
from utils import templates
from utils.time_helpers import fmt_date, fmt_time, today_local
from utils.validators import validate_reason

router = Router(name="admin")


def _is_admin(emp: Employee | None) -> bool:
    return emp is not None and emp.role in (Role.admin, Role.menejer) and emp.status == EmployeeStatus.faol


def _is_admin_or_super(from_user_id: int, emp: Employee | None) -> bool:
    return _is_admin(emp) or from_user_id in settings.super_admin_ids


# ==================== XODIM TASDIQLASH ====================
@router.callback_query(F.data.startswith("emp_ok:"))
async def emp_approve(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    emp_id = int(call.data.split(":")[1])
    emp = await approve_employee(session, emp_id, call.from_user.id)
    if not emp:
        await call.answer("Topilmadi", show_alert=True)
        return
    await log_action(session, employee.id, "approve_employee", {"emp_id": emp_id})
    await call.message.edit_text(f"✅ {emp.full_name} qabul qilindi.")
    await notify_employee(call.bot, emp, templates.APPROVED)
    await call.answer("Qabul qilindi")


@router.callback_query(F.data.startswith("emp_no:"))
async def emp_reject(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    emp_id = int(call.data.split(":")[1])
    emp = await reject_employee(session, emp_id, call.from_user.id)
    if not emp:
        await call.answer("Topilmadi", show_alert=True)
        return
    await log_action(session, employee.id, "reject_employee", {"emp_id": emp_id})
    await call.message.edit_text(f"❌ {emp.full_name} rad etildi.")
    await notify_employee(call.bot, emp, templates.REJECTED_EMP)
    await call.answer("Rad etildi")


# ==================== SO'ROVGA JAVOB ====================
async def _resolve_and_notify(call, session, employee, req_id, approve: bool, comment: str | None):
    req = await get_request(session, req_id)
    if not req or req.status != RequestStatus.kutilmoqda:
        await call.answer("So'rov allaqachon ko'rib chiqilgan", show_alert=True)
        return
    status = RequestStatus.tasdiqlandi if approve else RequestStatus.rad_etildi
    await resolve_request(session, req, status, call.from_user.id, comment)
    await log_action(session, employee.id, "resolve_request", {"req_id": req_id, "approve": approve})

    emp = await get_employee_by_id(session, req.employee_id)
    admin_name = employee.full_name
    if approve:
        text = templates.request_approved_emp(req.target_date, req.expected_time, admin_name, comment)
    else:
        text = templates.request_rejected_emp(req.target_date, req.expected_time, admin_name, comment)
    if emp:
        await notify_employee(call.bot, emp, text)

    verdict = "✅ Tasdiqlandi" if approve else "❌ Rad etildi"
    try:
        await call.message.edit_text(f"{call.message.text}\n\n➡️ {verdict} ({admin_name})")
    except Exception:
        await call.message.answer(f"➡️ {verdict}")


@router.callback_query(F.data.startswith("req_ok:"))
async def req_ok(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await _resolve_and_notify(call, session, employee, int(call.data.split(":")[1]), True, None)
    await call.answer()


@router.callback_query(F.data.startswith("req_no:"))
async def req_no(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await _resolve_and_notify(call, session, employee, int(call.data.split(":")[1]), False, None)
    await call.answer()


@router.callback_query(F.data.startswith("req_cm:"))
async def req_comment(call: CallbackQuery, state: FSMContext, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    req_id = int(call.data.split(":")[1])
    await state.set_state(AdminReview.comment)
    await state.update_data(req_id=req_id, attempts=0)
    await call.message.answer("💬 Izohingizni yozing (keyin tasdiqlash/rad etishni tanlaysiz):")
    await call.answer()


@router.message(AdminReview.comment, F.text)
async def req_comment_text(message: Message, state: FSMContext, session: AsyncSession, employee: Employee | None):
    ok, err = validate_reason(message.text)
    if not ok:
        data = await state.get_data()
        attempts = data.get("attempts", 0) + 1
        await state.update_data(attempts=attempts)
        if attempts >= 3:
            await message.answer("⚠️ Izoh qabul qilinmadi. Izohsiz tugmalardan foydalaning.")
            await state.clear()
            return
        await message.answer(err)
        return
    data = await state.get_data()
    await state.update_data(comment=message.text.strip())
    await message.answer(
        "Izoh saqlandi. Endi qarorni tanlang:",
        reply_markup=admin_kb.comment_decision_kb(data["req_id"]),
    )


@router.callback_query(F.data.startswith("reqc_ok:"))
async def reqc_ok(call: CallbackQuery, state: FSMContext, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    data = await state.get_data()
    comment = data.get("comment")
    await state.clear()
    await _resolve_and_notify(call, session, employee, int(call.data.split(":")[1]), True, comment)
    await call.answer()


@router.callback_query(F.data.startswith("reqc_no:"))
async def reqc_no(call: CallbackQuery, state: FSMContext, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    data = await state.get_data()
    comment = data.get("comment")
    await state.clear()
    await _resolve_and_notify(call, session, employee, int(call.data.split(":")[1]), False, comment)
    await call.answer()


# ==================== ADMIN AMALLARI (umumiy logika) ====================
async def _do_today(msg: Message, session: AsyncSession, employee: Employee):
    branch = employee.branch
    if branch:
        text = await today_branch_report(session, branch, today_local())
        await msg.answer(text)
    else:
        await msg.answer("ℹ️ Sizga filial biriktirilmagan.")


async def _do_pending(msg: Message, session: AsyncSession, employee: Employee):
    reqs = await list_pending_requests(session, employee.branch_id)
    if not reqs:
        await msg.answer("✅ Kutilayotgan so'rovlar yo'q.")
        return
    for req in reqs:
        emp = await get_employee_by_id(session, req.employee_id)
        head = "🕐 KECH QOLISH" if req.type == RequestType.kech_qolish else "🏖 DAM OLISH"
        mapping = uz.LATE_REQUEST_REASONS if req.type == RequestType.kech_qolish else uz.VACATION_REASONS
        reason = uz.reason_label(mapping, req.reason_code, req.reason_text)
        tline = f"\n⏰ Kelish: {fmt_time(req.expected_time)}" if req.expected_time else ""
        text = (
            f"{head} SO'ROVI\n\n"
            f"👤 {emp.full_name if emp else '—'}\n"
            f"📅 {fmt_date(req.target_date) if req.target_date else '—'}{tline}\n"
            f"📝 Sabab: {reason}"
        )
        await msg.answer(text, reply_markup=admin_kb.review_request_kb(req.id))


async def _do_outside(msg: Message, session: AsyncSession, employee: Employee):
    day = today_local()
    res = await session.execute(
        select(Break, Employee)
        .join(Employee, Break.employee_id == Employee.id)
        .where(and_(Break.date == day, Break.back_time.is_(None), Employee.branch_id == employee.branch_id))
    )
    rows = res.all()
    if not rows:
        await msg.answer("✅ Hozir hamma joyida.")
        return
    lines = ["⚠️ Hozir tashqarida:\n"]
    for br, emp in rows:
        reason = uz.reason_label(uz.BREAK_REASONS, br.reason_code, br.reason_text)
        lines.append(f"🚶 {emp.full_name} — {fmt_time(br.out_time)} dan ({reason})")
    await msg.answer("\n".join(lines))


async def _do_late(msg: Message, session: AsyncSession, employee: Employee):
    day = today_local()
    res = await session.execute(
        select(Attendance, Employee)
        .join(Employee, Attendance.employee_id == Employee.id)
        .where(and_(Attendance.date == day, Attendance.is_late.is_(True), Employee.branch_id == employee.branch_id))
    )
    rows = res.all()
    if not rows:
        await msg.answer("✅ Bugun kech qolganlar yo'q.")
        return
    lines = ["⏰ Bugun kech qolganlar:\n"]
    for att, emp in rows:
        lines.append(f"⚠️ {emp.full_name} — {fmt_time(att.check_in)} ({att.late_minutes}d kech)")
    await msg.answer("\n".join(lines))


async def _do_employees(msg: Message, session: AsyncSession, employee: Employee):
    emps = await list_branch_employees(session, employee.branch_id, only_active=False)
    if not emps:
        await msg.answer("👥 Xodimlar yo'q.")
        return
    await msg.answer(
        f"👥 Xodimlar ({len(emps)}):\nTahrirlash uchun xodimni tanlang:",
        reply_markup=admin_kb.employees_list_kb(emps),
    )


async def _do_excel(msg: Message, session: AsyncSession, employee: Employee):
    await msg.answer("⏳ Excel tayyorlanmoqda...")
    day = today_local()
    data = await excel_export.build_month_excel(session, employee.branch_id, day.year, day.month)
    fname = f"davomat_{day.year}_{day.month:02d}.xlsx"
    await msg.answer_document(BufferedInputFile(data, filename=fname))


async def _do_videos(msg: Message, session: AsyncSession, employee: Employee):
    """Bugungi kelish/ketish video-doiralarini (кружок) ko'rsatadi."""
    day = today_local()
    res = await session.execute(
        select(Attendance, Employee)
        .join(Employee, Attendance.employee_id == Employee.id)
        .where(and_(Attendance.date == day, Employee.branch_id == employee.branch_id))
        .order_by(Employee.full_name)
    )
    rows = res.all()
    sent = 0
    await msg.answer(f"🎥 Bugungi videolar — {employee.branch.name if employee.branch else '—'}")
    for att, emp in rows:
        if att.check_in_video_id:
            await msg.answer(f"✅ {emp.full_name} — Keldi {fmt_time(att.check_in)}")
            try:
                await msg.answer_video_note(att.check_in_video_id)
                sent += 1
            except Exception:
                await msg.answer("⚠️ Video yuklanmadi.")
        if att.check_out_video_id:
            await msg.answer(f"🚪 {emp.full_name} — Ketdi {fmt_time(att.check_out)}")
            try:
                await msg.answer_video_note(att.check_out_video_id)
                sent += 1
            except Exception:
                await msg.answer("⚠️ Video yuklanmadi.")
    if sent == 0:
        await msg.answer("ℹ️ Bugun hali video yo'q.")


# ==================== REPLY-TUGMA HANDLERLARI (asosiy klaviatura) ====================
@router.message(F.text == "📊 Bugungi hisobot")
async def btn_today(message: Message, session: AsyncSession, employee: Employee | None):
    if not _is_admin(employee):
        return
    await _do_today(message, session, employee)


@router.message(F.text == "⏳ Kutilayotgan so'rovlar")
async def btn_pending(message: Message, session: AsyncSession, employee: Employee | None):
    if not _is_admin(employee):
        return
    await _do_pending(message, session, employee)


@router.message(F.text == "⚠️ Hozir tashqarida")
async def btn_outside(message: Message, session: AsyncSession, employee: Employee | None):
    if not _is_admin(employee):
        return
    await _do_outside(message, session, employee)


@router.message(F.text == "⏰ Bugun kech qolganlar")
async def btn_late(message: Message, session: AsyncSession, employee: Employee | None):
    if not _is_admin(employee):
        return
    await _do_late(message, session, employee)


@router.message(F.text == "👥 Xodimlar")
async def btn_employees(message: Message, session: AsyncSession, employee: Employee | None):
    if not _is_admin(employee):
        return
    await _do_employees(message, session, employee)


@router.message(F.text == "📥 Excel")
async def btn_excel(message: Message, session: AsyncSession, employee: Employee | None):
    if not _is_admin(employee):
        return
    await _do_excel(message, session, employee)


@router.message(F.text == "🎥 Bugungi videolar")
async def btn_videos(message: Message, session: AsyncSession, employee: Employee | None):
    if not _is_admin(employee):
        return
    await _do_videos(message, session, employee)


# ==================== ESKI "ADMIN PANEL" (inline) — orqaga moslik ====================
@router.message(F.text == "🛠 Admin panel")
async def admin_panel(message: Message, session: AsyncSession, employee: Employee | None):
    if not _is_admin(employee):
        return
    pending = await list_pending_requests(session, employee.branch_id)
    await message.answer("🛠 Admin panel", reply_markup=admin_kb.admin_menu(len(pending)))


@router.callback_query(F.data == "adm:today")
async def adm_today(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await _do_today(call.message, session, employee)
    await call.answer()


@router.callback_query(F.data == "adm:pending")
async def adm_pending(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await _do_pending(call.message, session, employee)
    await call.answer()


@router.callback_query(F.data == "adm:outside")
async def adm_outside(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await _do_outside(call.message, session, employee)
    await call.answer()


@router.callback_query(F.data == "adm:late")
async def adm_late(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await _do_late(call.message, session, employee)
    await call.answer()


@router.callback_query(F.data == "adm:employees")
async def adm_employees(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await _do_employees(call.message, session, employee)
    await call.answer()


@router.callback_query(F.data == "adm:excel")
async def adm_excel(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer("Excel tayyorlanmoqda...")
    await _do_excel(call.message, session, employee)


@router.callback_query(F.data == "adm:videos")
async def adm_videos(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer("Videolar yuklanmoqda...")
    await _do_videos(call.message, session, employee)


@router.callback_query(F.data.in_({"adm:rating", "adm:bydate", "adm:settings"}))
async def adm_stub(call: CallbackQuery, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer("Bu bo'lim keyingi versiyada.", show_alert=True)


# ==================== XODIMNI TAHRIRLASH (rol / holat) ====================
def _emp_card_text(emp: Employee) -> str:
    role_uz = {"admin": "👑 Admin", "menejer": "🧑‍💼 Menejer", "xodim": "👷 Xodim"}.get(
        emp.role.value, emp.role.value
    )
    stat_uz = {"faol": "✅ Faol", "kutilmoqda": "⏳ Kutilmoqda", "faolsiz": "🚫 Bloklangan"}.get(
        emp.status.value, emp.status.value
    )
    return (
        f"👤 {emp.full_name}\n"
        f"📞 {emp.phone or '—'}\n"
        f"💼 {emp.position or '—'}\n"
        f"🏢 {emp.branch.name if emp.branch else '—'}\n"
        f"🔑 Rol: {role_uz}\n"
        f"📌 Holat: {stat_uz}\n\n"
        f"Rol yoki holatni o'zgartirish uchun tugmani bosing:"
    )


async def _show_emp_card(call: CallbackQuery, session: AsyncSession, emp_id: int):
    emp = await get_employee_by_id(session, emp_id)
    if not emp:
        await call.answer("Topilmadi", show_alert=True)
        return
    try:
        await call.message.edit_text(_emp_card_text(emp), reply_markup=admin_kb.employee_card_kb(emp))
    except Exception:
        await call.message.answer(_emp_card_text(emp), reply_markup=admin_kb.employee_card_kb(emp))


@router.callback_query(F.data.startswith("empmng:"))
async def emp_manage(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await _show_emp_card(call, session, int(call.data.split(":")[1]))
    await call.answer()


@router.callback_query(F.data.startswith("emprole:"))
async def emp_set_role(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    _, sid, role = call.data.split(":")
    emp = await get_employee_by_id(session, int(sid))
    if not emp:
        await call.answer("Topilmadi", show_alert=True)
        return
    emp.role = Role(role)
    if emp.status == EmployeeStatus.kutilmoqda:
        emp.status = EmployeeStatus.faol  # rol berilsa avtomatik faollashadi
    await session.commit()
    await log_action(session, employee.id, "set_role", {"emp_id": emp.id, "role": role})
    await call.answer(f"Rol o'zgartirildi: {role}")
    await _show_emp_card(call, session, emp.id)


@router.callback_query(F.data.startswith("empstat:"))
async def emp_set_status(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    _, sid, stat = call.data.split(":")
    emp = await get_employee_by_id(session, int(sid))
    if not emp:
        await call.answer("Topilmadi", show_alert=True)
        return
    emp.status = EmployeeStatus(stat)
    await session.commit()
    await log_action(session, employee.id, "set_status", {"emp_id": emp.id, "status": stat})
    if stat == "faol":
        await notify_employee(call.bot, emp, templates.APPROVED)
    else:
        await notify_employee(call.bot, emp, templates.REJECTED_EMP)
    await call.answer("Holat o'zgartirildi")
    await _show_emp_card(call, session, emp.id)


@router.callback_query(F.data == "empmng_list")
async def emp_back_list(call: CallbackQuery, session: AsyncSession, employee: Employee | None):
    if not _is_admin_or_super(call.from_user.id, employee):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    emps = await list_branch_employees(session, employee.branch_id, only_active=False)
    try:
        await call.message.edit_text(
            f"👥 Xodimlar ({len(emps)}):\nTahrirlash uchun xodimni tanlang:",
            reply_markup=admin_kb.employees_list_kb(emps),
        )
    except Exception:
        await call.message.answer(
            f"👥 Xodimlar ({len(emps)}):",
            reply_markup=admin_kb.employees_list_kb(emps),
        )
    await call.answer()

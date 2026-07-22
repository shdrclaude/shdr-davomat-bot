"""Hisobotlarni tayyorlash (xodim oylik + admin kunlik)."""
from __future__ import annotations

import calendar as _cal
from datetime import date, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Attendance,
    Break,
    DayType,
    Employee,
    EmployeeStatus,
)
from utils.time_helpers import MONTHS_UZ, fmt_duration_short, fmt_time


async def employee_month_stats(
    session: AsyncSession, emp: Employee, year: int, month: int
) -> dict:
    first = date(year, month, 1)
    last = date(year, month, _cal.monthrange(year, month)[1])

    res = await session.execute(
        select(Attendance).where(
            and_(
                Attendance.employee_id == emp.id,
                Attendance.date >= first,
                Attendance.date <= last,
            )
        )
    )
    rows = list(res.scalars().all())

    worked_days = sum(1 for r in rows if r.check_in and r.day_type == DayType.ish)
    dayoff_days = sum(1 for r in rows if r.day_type == DayType.dam_olish)
    absent_days = sum(1 for r in rows if r.day_type == DayType.kelmagan)
    total_minutes = sum(r.worked_minutes or 0 for r in rows)
    late_count = sum(1 for r in rows if r.is_late)
    late_minutes = sum(r.late_minutes or 0 for r in rows)

    bres = await session.execute(
        select(func.count(Break.id), func.coalesce(func.sum(Break.duration_minutes), 0)).where(
            and_(
                Break.employee_id == emp.id,
                Break.date >= first,
                Break.date <= last,
            )
        )
    )
    break_count, break_minutes = bres.one()

    avg_minutes = int(total_minutes / worked_days) if worked_days else 0

    rank, branch_total = await _branch_rank(session, emp, first, last, total_minutes)

    return {
        "worked_days": worked_days,
        "absent_days": absent_days,
        "dayoff_days": dayoff_days,
        "total_hours": round(total_minutes / 60, 1),
        "avg_minutes": avg_minutes,
        "late_count": late_count,
        "late_minutes": late_minutes,
        "break_count": break_count or 0,
        "break_minutes": break_minutes or 0,
        "rank": rank,
        "branch_total": branch_total,
        "month_label": f"{MONTHS_UZ[month].capitalize()} {year}",
    }


async def _branch_rank(session, emp, first, last, my_minutes) -> tuple[int, int]:
    if not emp.branch_id:
        return 1, 1
    res = await session.execute(
        select(Attendance.employee_id, func.sum(Attendance.worked_minutes))
        .join(Employee, Attendance.employee_id == Employee.id)
        .where(
            and_(
                Employee.branch_id == emp.branch_id,
                Employee.status == EmployeeStatus.faol,
                Attendance.date >= first,
                Attendance.date <= last,
            )
        )
        .group_by(Attendance.employee_id)
    )
    totals = {eid: (m or 0) for eid, m in res.all()}
    # faol xodimlar soni
    cnt = await session.execute(
        select(func.count(Employee.id)).where(
            and_(Employee.branch_id == emp.branch_id, Employee.status == EmployeeStatus.faol)
        )
    )
    branch_total = cnt.scalar_one() or 1
    ordered = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    rank = next((i + 1 for i, (eid, _) in enumerate(ordered) if eid == emp.id), branch_total)
    return rank, branch_total


async def today_branch_report(session: AsyncSession, branch, day: date) -> str:
    """Bitta filial uchun kunlik hisobot matni."""
    from utils.time_helpers import fmt_date

    res = await session.execute(
        select(Employee).where(
            and_(Employee.branch_id == branch.id, Employee.status == EmployeeStatus.faol)
        ).order_by(Employee.full_name)
    )
    employees = list(res.scalars().all())

    lines = [f"📊 HISOBOT — {fmt_date(day)}\n", f"🏢 {branch.name}", "━━━━━━━━━━━━━━━━━━"]
    came = late = absent = 0
    body = []
    for emp in employees:
        att = await session.execute(
            select(Attendance).where(
                and_(Attendance.employee_id == emp.id, Attendance.date == day)
            )
        )
        att = att.scalar_one_or_none()
        name = emp.full_name.split()[0] if emp.full_name else emp.full_name
        if att and att.day_type == DayType.dam_olish:
            body.append(f"🏖 {emp.full_name} — dam olishda")
            continue
        if not att or not att.check_in:
            absent += 1
            body.append(f"❌ {emp.full_name} — kelmagan")
            continue
        came += 1
        bc = await session.execute(
            select(func.count(Break.id)).where(
                and_(Break.employee_id == emp.id, Break.date == day)
            )
        )
        bc = bc.scalar_one() or 0
        icon = "✅"
        late_note = ""
        if att.is_late:
            late += 1
            icon = "⚠️"
            late_note = f" ({att.late_minutes}d kech)"
        if att.check_out:
            worked = fmt_duration_short(att.worked_minutes)
            body.append(
                f"{icon} {emp.full_name}\n"
                f"   {fmt_time(att.check_in)}{late_note} → {fmt_time(att.check_out)} · {worked} · 🚶{bc}"
            )
        else:
            body.append(
                f"{icon} {emp.full_name}\n"
                f"   {fmt_time(att.check_in)}{late_note} → ishda · 🚶{bc}"
            )

    total = came + absent
    lines.append(f"✅ Keldi: {came}/{total}   ⚠️ Kech: {late}   ❌ Kelmadi: {absent}\n")
    lines.extend(body)
    return "\n".join(lines)

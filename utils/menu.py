"""Xodim menyusi holatini aniqlash."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Branch, Employee
from database.queries import get_open_break, get_today_attendance
from utils.time_helpers import combine_local, now_local, today_local


async def determine_menu_state(session: AsyncSession, emp: Employee, branch: Branch | None) -> str:
    """'not_in' | 'working' | 'outside' | 'done'."""
    day = today_local()
    att = await get_today_attendance(session, emp.id, day)

    if att is None or att.check_in is None:
        return "not_in"

    if att.check_out is not None:
        return "done"

    # ishda — ochiq tanaffus bormi?
    open_br = await get_open_break(session, emp.id, day)
    if open_br is not None:
        return "outside"

    # ish vaqti tugagan bo'lsa ham, hali "Ketdim" bosilmagan — ishda hisoblanadi
    return "working"


def is_work_time_over(employee) -> bool:
    """Xodimning (yoki filialining) ish vaqti tugaganmi."""
    branch = getattr(employee, "branch", None)
    end_t = getattr(employee, "work_end", None) or (branch.work_end if branch else None)
    if not end_t:
        return False
    end_dt = combine_local(today_local(), end_t)
    return now_local() > end_dt

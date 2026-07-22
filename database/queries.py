"""Ma'lumotlar bazasi bilan ishlash funksiyalari (data access layer)."""
from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    ActionLog,
    Attendance,
    Branch,
    Break,
    DayType,
    Employee,
    EmployeeStatus,
    Request,
    RequestStatus,
    RequestType,
    Role,
)


# ==================== EMPLOYEE ====================
async def get_employee_by_tg(session: AsyncSession, telegram_id: int) -> Employee | None:
    res = await session.execute(
        select(Employee)
        .options(selectinload(Employee.branch))
        .where(Employee.telegram_id == telegram_id)
    )
    return res.scalar_one_or_none()


async def get_employee_by_id(session: AsyncSession, emp_id: int) -> Employee | None:
    res = await session.execute(
        select(Employee).options(selectinload(Employee.branch)).where(Employee.id == emp_id)
    )
    return res.scalar_one_or_none()


async def create_employee(
    session: AsyncSession,
    telegram_id: int,
    full_name: str,
    username: str | None,
    phone: str | None,
    branch_id: int,
    position: str,
) -> Employee:
    emp = Employee(
        telegram_id=telegram_id,
        full_name=full_name,
        username=username,
        phone=phone,
        branch_id=branch_id,
        position=position,
        role=Role.xodim,
        status=EmployeeStatus.kutilmoqda,
    )
    session.add(emp)
    await session.commit()
    await session.refresh(emp)
    return emp


async def approve_employee(session: AsyncSession, emp_id: int, admin_tg: int) -> Employee | None:
    emp = await get_employee_by_id(session, emp_id)
    if not emp:
        return None
    emp.status = EmployeeStatus.faol
    emp.approved_by = admin_tg
    await session.commit()
    return emp


async def reject_employee(session: AsyncSession, emp_id: int, admin_tg: int) -> Employee | None:
    emp = await get_employee_by_id(session, emp_id)
    if not emp:
        return None
    emp.status = EmployeeStatus.faolsiz
    emp.approved_by = admin_tg
    await session.commit()
    return emp


async def list_branch_employees(
    session: AsyncSession, branch_id: int, only_active: bool = True
) -> list[Employee]:
    q = select(Employee).where(Employee.branch_id == branch_id)
    if only_active:
        q = q.where(Employee.status == EmployeeStatus.faol)
    q = q.order_by(Employee.full_name)
    res = await session.execute(q)
    return list(res.scalars().all())


async def list_admins_for_branch(session: AsyncSession, branch_id: int) -> list[Employee]:
    res = await session.execute(
        select(Employee).where(
            and_(
                Employee.branch_id == branch_id,
                Employee.role.in_([Role.admin, Role.menejer]),
                Employee.status == EmployeeStatus.faol,
            )
        )
    )
    return list(res.scalars().all())


# ==================== BRANCH ====================
async def list_branches(session: AsyncSession) -> list[Branch]:
    res = await session.execute(select(Branch).order_by(Branch.name))
    return list(res.scalars().all())


async def get_branch(session: AsyncSession, branch_id: int) -> Branch | None:
    res = await session.execute(select(Branch).where(Branch.id == branch_id))
    return res.scalar_one_or_none()


async def create_branch(session: AsyncSession, name: str, **kwargs) -> Branch:
    br = Branch(name=name, **kwargs)
    session.add(br)
    await session.commit()
    await session.refresh(br)
    return br


# ==================== ATTENDANCE ====================
async def get_today_attendance(
    session: AsyncSession, emp_id: int, day: date
) -> Attendance | None:
    res = await session.execute(
        select(Attendance).where(
            and_(Attendance.employee_id == emp_id, Attendance.date == day)
        )
    )
    return res.scalar_one_or_none()


async def create_check_in(
    session: AsyncSession,
    emp_id: int,
    day: date,
    check_in: datetime,
    video_id: str,
    is_late: bool,
    late_minutes: int,
) -> Attendance:
    att = Attendance(
        employee_id=emp_id,
        date=day,
        check_in=check_in,
        check_in_video_id=video_id,
        is_late=is_late,
        late_minutes=late_minutes,
        day_type=DayType.ish,
    )
    session.add(att)
    await session.commit()
    await session.refresh(att)
    return att


async def set_check_out(
    session: AsyncSession,
    att: Attendance,
    check_out: datetime,
    video_id: str,
    worked_minutes: int,
    break_minutes: int,
) -> Attendance:
    att.check_out = check_out
    att.check_out_video_id = video_id
    att.worked_minutes = worked_minutes
    att.break_minutes = break_minutes
    await session.commit()
    return att


# ==================== BREAKS ====================
async def count_breaks_today(session: AsyncSession, emp_id: int, day: date) -> int:
    res = await session.execute(
        select(func.count(Break.id)).where(
            and_(Break.employee_id == emp_id, Break.date == day)
        )
    )
    return res.scalar_one()


async def get_open_break(session: AsyncSession, emp_id: int, day: date) -> Break | None:
    res = await session.execute(
        select(Break).where(
            and_(
                Break.employee_id == emp_id,
                Break.date == day,
                Break.back_time.is_(None),
            )
        )
    )
    return res.scalar_one_or_none()


async def create_break(
    session: AsyncSession,
    emp_id: int,
    day: date,
    out_time: datetime,
    reason_code: str,
    reason_text: str | None,
    expected_minutes: int,
) -> Break:
    br = Break(
        employee_id=emp_id,
        date=day,
        out_time=out_time,
        reason_code=reason_code,
        reason_text=reason_text,
        expected_minutes=expected_minutes,
    )
    session.add(br)
    await session.commit()
    await session.refresh(br)
    return br


async def close_break(
    session: AsyncSession, br: Break, back_time: datetime, duration: int, is_overdue: bool
) -> Break:
    br.back_time = back_time
    br.duration_minutes = duration
    br.is_overdue = is_overdue
    await session.commit()
    return br


async def get_overdue_open_breaks(session: AsyncSession) -> list[Break]:
    """Hali qaytmagan ochiq tanaffuslar."""
    res = await session.execute(
        select(Break)
        .where(Break.back_time.is_(None))
        .order_by(Break.out_time)
    )
    return list(res.scalars().all())


async def sum_break_minutes(session: AsyncSession, emp_id: int, day: date) -> int:
    res = await session.execute(
        select(func.coalesce(func.sum(Break.duration_minutes), 0)).where(
            and_(Break.employee_id == emp_id, Break.date == day)
        )
    )
    return res.scalar_one() or 0


# ==================== REQUESTS ====================
async def create_request(
    session: AsyncSession,
    emp_id: int,
    rtype: RequestType,
    target_date: date | None,
    expected_time: time | None,
    reason_code: str | None,
    reason_text: str | None,
    end_date: date | None = None,
) -> Request:
    req = Request(
        employee_id=emp_id,
        type=rtype,
        target_date=target_date,
        end_date=end_date,
        expected_time=expected_time,
        reason_code=reason_code,
        reason_text=reason_text,
        status=RequestStatus.kutilmoqda,
    )
    session.add(req)
    await session.commit()
    await session.refresh(req)
    return req


async def get_request(session: AsyncSession, req_id: int) -> Request | None:
    res = await session.execute(select(Request).where(Request.id == req_id))
    return res.scalar_one_or_none()


async def resolve_request(
    session: AsyncSession,
    req: Request,
    status: RequestStatus,
    admin_tg: int,
    comment: str | None,
) -> Request:
    req.status = status
    req.reviewed_by = admin_tg
    req.admin_comment = comment
    req.resolved_at = datetime.utcnow()
    await session.commit()
    return req


async def count_pending_late_today(session: AsyncSession, emp_id: int, day: date) -> int:
    """Bugun yaratilgan kech qolish so'rovlari soni (limit 1/kun)."""
    res = await session.execute(
        select(func.count(Request.id)).where(
            and_(
                Request.employee_id == emp_id,
                Request.type == RequestType.kech_qolish,
                func.date(Request.created_at) == day,
            )
        )
    )
    return res.scalar_one()


async def get_last_pending_late(session: AsyncSession, emp_id: int, day: date) -> Request | None:
    res = await session.execute(
        select(Request)
        .where(
            and_(
                Request.employee_id == emp_id,
                Request.type == RequestType.kech_qolish,
                func.date(Request.created_at) == day,
            )
        )
        .order_by(Request.created_at.desc())
    )
    return res.scalars().first()


async def count_pending_vacation_month(session: AsyncSession, emp_id: int, month_start: date) -> int:
    """Oy boshidan buyon kutilayotgan dam olish so'rovlari (limit 3/oy)."""
    res = await session.execute(
        select(func.count(Request.id)).where(
            and_(
                Request.employee_id == emp_id,
                Request.type == RequestType.dam_olish,
                Request.status == RequestStatus.kutilmoqda,
                Request.created_at >= month_start,
            )
        )
    )
    return res.scalar_one()


async def find_recent_duplicate(
    session: AsyncSession,
    emp_id: int,
    rtype: RequestType,
    since: datetime,
) -> Request | None:
    """5 daqiqa ichida bir xil turdagi so'rovni topadi."""
    res = await session.execute(
        select(Request).where(
            and_(
                Request.employee_id == emp_id,
                Request.type == rtype,
                Request.created_at >= since,
            )
        )
    )
    return res.scalars().first()


async def list_pending_requests(session: AsyncSession, branch_id: int) -> list[Request]:
    res = await session.execute(
        select(Request)
        .join(Employee, Request.employee_id == Employee.id)
        .where(
            and_(
                Employee.branch_id == branch_id,
                Request.status == RequestStatus.kutilmoqda,
            )
        )
        .order_by(Request.created_at)
    )
    return list(res.scalars().all())


# ==================== ACTION LOG ====================
async def log_action(
    session: AsyncSession, emp_id: int | None, action: str, payload: dict | None = None
) -> None:
    session.add(ActionLog(employee_id=emp_id, action=action, payload=payload))
    await session.commit()


# ==================== SUPERVISORS (nazoratchilar) ====================
async def upsert_supervisor(session: AsyncSession, telegram_id: int, username: str | None):
    from database.models import Supervisor
    res = await session.execute(select(Supervisor).where(Supervisor.telegram_id == telegram_id))
    sup = res.scalar_one_or_none()
    if sup:
        sup.username = username
    else:
        session.add(Supervisor(telegram_id=telegram_id, username=username))
    await session.commit()


async def list_supervisors(session: AsyncSession):
    from database.models import Supervisor
    res = await session.execute(select(Supervisor))
    return list(res.scalars().all())


async def list_all_employees(session: AsyncSession, only_active: bool = False) -> list[Employee]:
    """Barcha filiallar xodimlari (super-admin ko'rinishi uchun)."""
    q = select(Employee).options(selectinload(Employee.branch))
    if only_active:
        q = q.where(Employee.status == EmployeeStatus.faol)
    q = q.order_by(Employee.branch_id, Employee.full_name)
    res = await session.execute(q)
    return list(res.scalars().all())

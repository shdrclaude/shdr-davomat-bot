"""APScheduler avtomatik vazifalari."""
from __future__ import annotations

import logging
from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import and_, select

from config import settings
from database.models import (
    Attendance,
    Branch,
    Break,
    DayType,
    Employee,
    EmployeeStatus,
)
from database.queries import list_branches
from database.session import async_session_maker
from services.notifier import notify_branch_admins, safe_send
from services.report_builder import today_branch_report
from utils import templates
from utils.time_helpers import (
    combine_local,
    fmt_time,
    is_workday,
    minutes_between,
    now_local,
    today_local,
)

logger = logging.getLogger("shdr_bot")

BREAK_REMIND_AFTER = 10   # daqiqa — xodimga eslatma
BREAK_ADMIN_AFTER = 30    # daqiqa — adminga xabar


def setup_scheduler(bot) -> AsyncIOScheduler:
    sched = AsyncIOScheduler(timezone=settings.tz_name)

    sched.add_job(morning_greeting, CronTrigger(hour=7, minute=45), args=[bot], id="morning")
    sched.add_job(absentees_to_admin, CronTrigger(hour=8, minute=30), args=[bot], id="absentees")
    sched.add_job(remind_not_checked, CronTrigger(hour=9, minute=0), args=[bot], id="remind_checkin")
    sched.add_job(check_overdue_breaks, IntervalTrigger(minutes=15), args=[bot], id="breaks")
    sched.add_job(remind_checkout, CronTrigger(hour=18, minute=30), args=[bot], id="remind_out")
    sched.add_job(daily_report, CronTrigger(hour=19, minute=0), args=[bot], id="daily")
    sched.add_job(weekly_report, CronTrigger(day_of_week="mon", hour=9, minute=0), args=[bot], id="weekly")
    sched.add_job(monthly_excel, CronTrigger(day=1, hour=8, minute=0), args=[bot], id="monthly")
    return sched


async def _active_branches_today(session):
    branches = await list_branches(session)
    day = today_local()
    return [b for b in branches if is_workday(day, b.work_days)]


async def morning_greeting(bot):
    async with async_session_maker() as session:
        day = today_local()
        for branch in await _active_branches_today(session):
            res = await session.execute(
                select(Employee).where(
                    and_(Employee.branch_id == branch.id, Employee.status == EmployeeStatus.faol)
                )
            )
            for emp in res.scalars().all():
                await safe_send(bot, emp.telegram_id, "🌅 Xayrli tong! 15 daqiqadan keyin ish boshlanadi.")


async def absentees_to_admin(bot):
    async with async_session_maker() as session:
        day = today_local()
        for branch in await _active_branches_today(session):
            res = await session.execute(
                select(Employee).where(
                    and_(Employee.branch_id == branch.id, Employee.status == EmployeeStatus.faol)
                )
            )
            absent = []
            for emp in res.scalars().all():
                att = await session.execute(
                    select(Attendance).where(
                        and_(Attendance.employee_id == emp.id, Attendance.date == day)
                    )
                )
                att = att.scalar_one_or_none()
                if not att or not att.check_in:
                    absent.append(emp.full_name)
            if absent:
                text = "📋 Hali kelmaganlar:\n\n" + "\n".join(f"❌ {n}" for n in absent)
                await notify_branch_admins(bot, session, branch.id, text)


async def remind_not_checked(bot):
    async with async_session_maker() as session:
        day = today_local()
        for branch in await _active_branches_today(session):
            res = await session.execute(
                select(Employee).where(
                    and_(Employee.branch_id == branch.id, Employee.status == EmployeeStatus.faol)
                )
            )
            for emp in res.scalars().all():
                att = await session.execute(
                    select(Attendance).where(
                        and_(Attendance.employee_id == emp.id, Attendance.date == day)
                    )
                )
                att = att.scalar_one_or_none()
                if not att or not att.check_in:
                    await safe_send(bot, emp.telegram_id,
                                    'ℹ️ Siz hali "✅ Keldim" tugmasini bosmadingiz.')


async def check_overdue_breaks(bot):
    async with async_session_maker() as session:
        now = now_local()
        res = await session.execute(
            select(Break, Employee, Branch)
            .join(Employee, Break.employee_id == Employee.id)
            .join(Branch, Employee.branch_id == Branch.id)
            .where(Break.back_time.is_(None))
        )
        from locales import uz
        for br, emp, branch in res.all():
            elapsed = minutes_between(br.out_time, now)
            expected = br.expected_minutes or 0
            reason = uz.reason_label(uz.BREAK_REASONS, br.reason_code, br.reason_text)
            expected_back = br.out_time + timedelta(minutes=expected)

            if elapsed >= expected + BREAK_REMIND_AFTER and not br.warned_10:
                await safe_send(bot, emp.telegram_id, templates.BREAK_REMIND_EMP)
                br.warned_10 = True
                await session.commit()

            if elapsed >= expected + BREAK_ADMIN_AFTER and not br.warned_admin:
                await notify_branch_admins(
                    bot, session, branch.id,
                    templates.admin_break_overdue(
                        emp.full_name, branch.name, br.out_time, expected_back, reason,
                    ),
                )
                br.warned_admin = True
                await session.commit()


async def remind_checkout(bot):
    async with async_session_maker() as session:
        day = today_local()
        res = await session.execute(
            select(Attendance, Employee)
            .join(Employee, Attendance.employee_id == Employee.id)
            .where(and_(Attendance.date == day, Attendance.check_in.isnot(None), Attendance.check_out.is_(None)))
        )
        for att, emp in res.all():
            await safe_send(bot, emp.telegram_id, '🚪 "Ketdim" tugmasini bosishni unutmang.')


async def daily_report(bot):
    async with async_session_maker() as session:
        day = today_local()
        for branch in await list_branches(session):
            if not is_workday(day, branch.work_days):
                continue
            text = await today_branch_report(session, branch, day)
            await notify_branch_admins(bot, session, branch.id, text)


async def weekly_report(bot):
    async with async_session_maker() as session:
        for branch in await list_branches(session):
            await notify_branch_admins(bot, session, branch.id, "📅 Haftalik hisobot tayyor (Admin panel → Excel).")


async def monthly_excel(bot):
    from services.excel_export import build_month_excel
    from aiogram.types import BufferedInputFile
    async with async_session_maker() as session:
        day = today_local()
        year, month = (day.year, day.month - 1) if day.month > 1 else (day.year - 1, 12)
        for branch in await list_branches(session):
            if not branch.admin_chat_id:
                continue
            data = await build_month_excel(session, branch.id, year, month)
            try:
                await bot.send_document(
                    branch.admin_chat_id,
                    BufferedInputFile(data, filename=f"davomat_{year}_{month:02d}.xlsx"),
                    caption="📥 Oylik davomat hisoboti",
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("Oylik excel yuborilmadi: %s", e)

"""SQLAlchemy async modellar."""
from __future__ import annotations

import enum
from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# === ENUM lar ===
class Role(str, enum.Enum):
    xodim = "xodim"
    menejer = "menejer"
    admin = "admin"


class EmployeeStatus(str, enum.Enum):
    kutilmoqda = "kutilmoqda"
    faol = "faol"
    faolsiz = "faolsiz"


class DayType(str, enum.Enum):
    ish = "ish"
    dam_olish = "dam_olish"
    bayram = "bayram"
    kelmagan = "kelmagan"


class RequestType(str, enum.Enum):
    kech_qolish = "kech_qolish"
    dam_olish = "dam_olish"
    erta_ketish = "erta_ketish"


class RequestStatus(str, enum.Enum):
    kutilmoqda = "kutilmoqda"
    tasdiqlandi = "tasdiqlandi"
    rad_etildi = "rad_etildi"
    bekor_qilindi = "bekor_qilindi"


# === Jadvallar ===
class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    work_start: Mapped[time] = mapped_column(Time, default=time(9, 0))
    work_end: Mapped[time] = mapped_column(Time, default=time(18, 0))
    lunch_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    lunch_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    work_days: Mapped[str] = mapped_column(String(32), default="1,2,3,4,5,6")
    admin_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employees: Mapped[list["Employee"]] = relationship(back_populates="branch")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[Role] = mapped_column(Enum(Role, name="role_enum"), default=Role.xodim)
    status: Mapped[EmployeeStatus] = mapped_column(
        Enum(EmployeeStatus, name="employee_status_enum"), default=EmployeeStatus.kutilmoqda
    )
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    approved_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    work_start: Mapped[time | None] = mapped_column(Time, nullable=True)  # shaxsiy ish vaqti (yo'q bo'lsa filialniki)
    work_end: Mapped[time | None] = mapped_column(Time, nullable=True)

    branch: Mapped["Branch"] = relationship(back_populates="employees")


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "date", name="uq_attendance_emp_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_in_video_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    check_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out_video_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    worked_minutes: Mapped[int] = mapped_column(Integer, default=0)
    break_minutes: Mapped[int] = mapped_column(Integer, default=0)
    day_type: Mapped[DayType] = mapped_column(
        Enum(DayType, name="day_type_enum"), default=DayType.ish
    )


class Break(Base):
    __tablename__ = "breaks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    out_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    back_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_overdue: Mapped[bool] = mapped_column(Boolean, default=False)
    warned_10: Mapped[bool] = mapped_column(Boolean, default=False)  # xodimga eslatma yuborildi
    warned_admin: Mapped[bool] = mapped_column(Boolean, default=False)  # adminga xabar yuborildi


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    type: Mapped[RequestType] = mapped_column(Enum(RequestType, name="request_type_enum"))
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # bir necha kunlik dam olish
    expected_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus, name="request_status_enum"), default=RequestStatus.kutilmoqda
    )
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    admin_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ActionLog(Base):
    __tablename__ = "action_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Supervisor(Base):
    __tablename__ = "supervisors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

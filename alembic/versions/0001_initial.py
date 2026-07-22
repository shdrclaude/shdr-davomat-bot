"""boshlang'ich sxema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


role_enum = sa.Enum("xodim", "menejer", "admin", name="role_enum")
emp_status_enum = sa.Enum("kutilmoqda", "faol", "faolsiz", name="employee_status_enum")
day_type_enum = sa.Enum("ish", "dam_olish", "bayram", "kelmagan", name="day_type_enum")
req_type_enum = sa.Enum("kech_qolish", "dam_olish", "erta_ketish", name="request_type_enum")
req_status_enum = sa.Enum(
    "kutilmoqda", "tasdiqlandi", "rad_etildi", "bekor_qilindi", name="request_status_enum"
)


def upgrade() -> None:
    op.create_table(
        "branches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("work_start", sa.Time(), nullable=True),
        sa.Column("work_end", sa.Time(), nullable=True),
        sa.Column("lunch_start", sa.Time(), nullable=True),
        sa.Column("lunch_end", sa.Time(), nullable=True),
        sa.Column("work_days", sa.String(length=32), nullable=True),
        sa.Column("admin_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("position", sa.String(length=64), nullable=True),
        sa.Column("role", role_enum, nullable=False, server_default="xodim"),
        sa.Column("status", emp_status_enum, nullable=False, server_default="kutilmoqda"),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("approved_by", sa.BigInteger(), nullable=True),
        sa.UniqueConstraint("telegram_id", name="uq_employees_telegram_id"),
    )

    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("check_in", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_in_video_id", sa.Text(), nullable=True),
        sa.Column("check_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_out_video_id", sa.Text(), nullable=True),
        sa.Column("is_late", sa.Boolean(), server_default=sa.false()),
        sa.Column("late_minutes", sa.Integer(), server_default="0"),
        sa.Column("worked_minutes", sa.Integer(), server_default="0"),
        sa.Column("break_minutes", sa.Integer(), server_default="0"),
        sa.Column("day_type", day_type_enum, nullable=False, server_default="ish"),
        sa.UniqueConstraint("employee_id", "date", name="uq_attendance_emp_date"),
    )

    op.create_table(
        "breaks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("out_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("back_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason_code", sa.String(length=32), nullable=True),
        sa.Column("reason_text", sa.Text(), nullable=True),
        sa.Column("expected_minutes", sa.Integer(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("is_overdue", sa.Boolean(), server_default=sa.false()),
        sa.Column("warned_10", sa.Boolean(), server_default=sa.false()),
        sa.Column("warned_admin", sa.Boolean(), server_default=sa.false()),
    )

    op.create_table(
        "requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("type", req_type_enum, nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("expected_time", sa.Time(), nullable=True),
        sa.Column("reason_code", sa.String(length=32), nullable=True),
        sa.Column("reason_text", sa.Text(), nullable=True),
        sa.Column("status", req_status_enum, nullable=False, server_default="kutilmoqda"),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("admin_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "action_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_attendance_date", "attendance", ["date"])
    op.create_index("ix_breaks_date", "breaks", ["date"])
    op.create_index("ix_requests_status", "requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_requests_status", table_name="requests")
    op.drop_index("ix_breaks_date", table_name="breaks")
    op.drop_index("ix_attendance_date", table_name="attendance")
    op.drop_table("action_log")
    op.drop_table("requests")
    op.drop_table("breaks")
    op.drop_table("attendance")
    op.drop_table("employees")
    op.drop_table("branches")
    for e in (req_status_enum, req_type_enum, day_type_enum, emp_status_enum, role_enum):
        e.drop(op.get_bind(), checkfirst=True)

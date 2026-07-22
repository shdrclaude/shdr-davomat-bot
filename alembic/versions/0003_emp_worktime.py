"""xodim shaxsiy ish vaqti

Revision ID: 0003_emp_worktime
Revises: 0002_supervisors
Create Date: 2026-07-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_emp_worktime"
down_revision: Union[str, None] = "0002_supervisors"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("work_start", sa.Time(), nullable=True))
    op.add_column("employees", sa.Column("work_end", sa.Time(), nullable=True))


def downgrade() -> None:
    op.drop_column("employees", "work_end")
    op.drop_column("employees", "work_start")

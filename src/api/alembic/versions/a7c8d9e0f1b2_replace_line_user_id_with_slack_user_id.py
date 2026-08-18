"""replace line user id with slack user id

Revision ID: a7c8d9e0f1b2
Revises: d5e6f7a8b9c0
Create Date: 2026-08-18 00:00:00.000000

LINEとSlackのUser IDに互換性はないため、既存値は移行せず通知先を再登録する。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7c8d9e0f1b2"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("users", "line_user_id")
    op.add_column("users", sa.Column("slack_user_id", sa.String(length=100), nullable=True))
    op.create_unique_constraint("uq_users_slack_user_id", "users", ["slack_user_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_slack_user_id", "users", type_="unique")
    op.drop_column("users", "slack_user_id")
    op.add_column("users", sa.Column("line_user_id", sa.String(length=100), nullable=True))
    op.create_unique_constraint("uq_users_line_user_id", "users", ["line_user_id"])

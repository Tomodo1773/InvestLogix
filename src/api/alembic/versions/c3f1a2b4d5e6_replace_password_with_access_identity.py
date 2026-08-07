"""replace password hash with cloudflare access identity

Revision ID: c3f1a2b4d5e6
Revises: 1f2e3d4c5b6a
Create Date: 2026-08-07 16:30:00.000000

認証をCloudflare Accessへ移行し、usersからパスワードハッシュを削除して
Accessの外部ID (issuer, sub) の紐付け列を追加する。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f1a2b4d5e6"
down_revision: str | None = "1f2e3d4c5b6a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("access_issuer", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("access_subject", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_users_access_identity", "users", ["access_issuer", "access_subject"])
    op.drop_column("users", "password_hash")


def downgrade() -> None:
    # ハッシュは復元できないため、既存行にはログイン不能なプレースホルダを入れる
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=False, server_default=""),
    )
    op.alter_column("users", "password_hash", server_default=None)
    op.drop_constraint("uq_users_access_identity", "users", type_="unique")
    op.drop_column("users", "access_subject")
    op.drop_column("users", "access_issuer")

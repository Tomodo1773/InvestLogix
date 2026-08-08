"""drop cloudflare access identity columns from users

Revision ID: d5e6f7a8b9c0
Revises: c3f1a2b4d5e6
Create Date: 2026-08-08 10:00:00.000000

Cloudflare Access との紐付けキーを (issuer, sub) から email へ移す。
JWTの `sub` は Access application ごとに変わりうるため、WebとMCPで別々の
application を使う構成では共通の紐付けキーにできない。email は Access が
確認済みのクレームで、users.email には既に一意制約があるためそのまま使える。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c3f1a2b4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_users_access_identity", "users", type_="unique")
    op.drop_column("users", "access_subject")
    op.drop_column("users", "access_issuer")


def downgrade() -> None:
    # 紐付け値は復元できない。列を戻したうえで、次のログインで再度紐付けさせる
    op.add_column("users", sa.Column("access_issuer", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("access_subject", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_users_access_identity", "users", ["access_issuer", "access_subject"])

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from stock.database import set_rls_user_id


@pytest.mark.asyncio
async def test_set_rls_user_id_sets_current_setting(db_session: AsyncSession):
    """set_rls_user_id が current_setting に user_id を設定できること"""
    await set_rls_user_id(db_session, 123)

    result = await db_session.execute(text("SELECT current_setting('app.current_user_id', true)"))

    assert result.scalar_one() == "123"

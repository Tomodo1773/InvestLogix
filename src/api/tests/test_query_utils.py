"""query_utils のテスト"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from stock.utils.query_utils import get_jst_extract_columns


@pytest.mark.asyncio
async def test_get_jst_extract_columns_returns_year_and_month(db_session: AsyncSession):
    """get_jst_extract_columns が年と月のラベル付きカラムを返すこと"""
    from stock import models

    # 関数を呼び出して年月カラムを取得
    year, month = get_jst_extract_columns(models.Transaction.transaction_date)

    # ラベルが正しいことを確認
    assert year.name == "year"
    assert month.name == "month"

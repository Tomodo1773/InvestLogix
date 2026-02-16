"""query_utils のテスト"""

import pytest
from sqlalchemy import select
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


@pytest.mark.asyncio
async def test_get_jst_extract_columns_works_in_query(db_session: AsyncSession):
    """get_jst_extract_columns がクエリ内で正常に動作すること"""
    from stock import models

    # 関数を使ってクエリを作成
    year, month = get_jst_extract_columns(models.Transaction.transaction_date)
    query = select(year, month)

    # クエリが正常にコンパイルできることを確認（実行はせず構文チェックのみ）
    compiled = query.compile()
    compiled_str = str(compiled)
    assert "AT TIME ZONE" in compiled_str
    assert "EXTRACT" in compiled_str.upper()
    # バインドパラメータに Asia/Tokyo が含まれていることを確認
    assert "Asia/Tokyo" in str(compiled.params.values())

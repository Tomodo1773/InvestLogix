"""SQLAlchemy クエリ用のユーティリティ関数"""

from sqlalchemy import ColumnElement, extract
from sqlalchemy.sql.elements import Label


def get_jst_extract_columns(date_column: ColumnElement) -> tuple[Label, Label]:
    """JSTベースの年月抽出カラムを返す

    データベースに保存されているUTC日時をJST（Asia/Tokyo）に変換し、
    年と月を抽出したSQLAlchemyのラベル付きカラムを返します。

    Args:
        date_column: 日時カラム（通常はUTCで保存されている）

    Returns:
        tuple[Label, Label]: (year, month) のラベル付きカラム

    Example:
        >>> year, month = get_jst_extract_columns(models.Transaction.transaction_date)
        >>> query = select(year, month, func.sum(...)).group_by(year, month)
    """
    date_jst = date_column.op("AT TIME ZONE")("Asia/Tokyo")
    year = extract("year", date_jst).label("year")
    month = extract("month", date_jst).label("month")
    return year, month

"""サービス層のドメインエラー

外部APIクライアントを抱えるサービスモジュールに例外を置くと、
例外を使いたいだけのモジュールがその依存をまとめて引き込むため、ここに集約する。

HTTPステータスへの変換は app.py の例外ハンドラで行うので、
各ルートで try/except して HTTPException に詰め替える必要はない。
"""


class StockNotFoundError(ValueError):
    """銘柄が見つからない場合のエラー"""


class DuplicateStockSplitError(ValueError):
    """同一銘柄・同一分割基準日の分割情報がすでに登録されている場合のエラー"""

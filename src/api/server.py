"""
アプリケーション起動スクリプト
開発サーバーの設定と起動を行う
"""

import uvicorn

from stock.app import app
from stock.database import settings

if __name__ == "__main__":
    # 開発サーバーの設定
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,  # 開発時のホットリロードを環境変数から設定
        log_level=settings.LOG_LEVEL.value,  # Enumの値を文字列として取得
    )

"""
アプリケーション起動スクリプト
開発サーバーの設定と起動を行う
"""

from stock.app import app

if __name__ == "__main__":
    import uvicorn

    # 開発サーバーの設定
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,  # 開発時のホットリロードを有効化
        log_level="info",  # ログレベルをinfoに設定
    )

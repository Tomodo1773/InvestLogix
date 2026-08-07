"""
FastAPIアプリケーション定義
ルーティングとミドルウェアの設定を行う
"""

from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse

from .auth import get_access_identity
from .routes import (
    dividends,
    holdings,
    portfolio,
    price_history,
    stock_splits,
    stocks,
    transactions,
    users,
)
from .services.errors import DuplicateStockSplitError, StockNotFoundError

# FastAPIアプリケーションの作成
#
# Cloudflare Access の検証をアプリ全体の依存性として掛ける。ルート単位で書くと
# 追加したルートで書き忘れたときに素通りするため、既定を「認証必須」にしている。
# ルート側の get_current_user はこの検証結果を再利用する（1リクエストにつき検証は1回）。
app = FastAPI(
    title="InvestLogix API",
    description="株式投資ポートフォリオ管理APIサービス",
    version="1.0.0",
    dependencies=[Depends(get_access_identity)],
)

# CORSミドルウェアは持たない。ブラウザからのアクセスはCloudflare Worker経由の
# 同一オリジンリクエストになり、/docs もAPI自身が同一オリジンで配信するため不要。


# ドメインエラーからHTTPレスポンスへの変換をここに集約する。
# detailはWeb側でそのまま利用者に表示されるため日本語にする。
@app.exception_handler(StockNotFoundError)
async def handle_stock_not_found(request: Request, exc: StockNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "指定された銘柄は登録されていません"},
    )


@app.exception_handler(DuplicateStockSplitError)
async def handle_duplicate_stock_split(request: Request, exc: DuplicateStockSplitError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "同じ銘柄・同じ分割基準日の株式分割がすでに登録されています"},
    )


# 各機能のエンドポイント
app.include_router(holdings.router, prefix="/api/v1/holdings", tags=["holdings"])
app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(price_history.router, prefix="/api/v1/symbols", tags=["symbols"])
app.include_router(stock_splits.router, prefix="/api/v1/stock-splits", tags=["stock-splits"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(dividends.router, prefix="/api/v1/dividends", tags=["dividends"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

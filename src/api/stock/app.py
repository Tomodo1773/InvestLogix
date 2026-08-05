"""
FastAPIアプリケーション定義
ルーティングとミドルウェアの設定を行う
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from .routes import (
    auth,
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
app = FastAPI(
    title="InvestLogix API",
    description="株式投資ポートフォリオ管理APIサービス",
    version="1.0.0",
)

# CORSミドルウェアは持たない。Webフロントは同一オリジンの /api をVercel Functionで中継しており、
# ブラウザからのクロスオリジンリクエストを許可する必要がないため。


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


# API基本情報のエンドポイント（テスト用）
@app.get("/", include_in_schema=True)
async def root():
    """
    APIのルートエンドポイント
    - 戻り値: APIの基本情報
    """
    return {
        "name": "InvestLogix API",
        "version": "1.0.0",
        "description": "株式投資ポートフォリオ管理APIサービス",
    }


# 認証関連のエンドポイント（トークン取得とユーザー登録）
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])

# 各機能のエンドポイント
app.include_router(holdings.router, prefix="/api/v1/holdings", tags=["holdings"])
app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(price_history.router, prefix="/api/v1/symbols", tags=["symbols"])
app.include_router(stock_splits.router, prefix="/api/v1/stock-splits", tags=["stock-splits"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(dividends.router, prefix="/api/v1/dividends", tags=["dividends"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

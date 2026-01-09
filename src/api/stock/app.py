"""
FastAPIアプリケーション定義
ルーティングとミドルウェアの設定を行う
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import settings
from .routes import auth, dividends, holdings, portfolio, stock_splits, stocks, transactions, users

# FastAPIアプリケーションの作成
app = FastAPI(
    title="InvestLogix API",
    description="株式投資ポートフォリオ管理APIサービス",
    version="1.0.0",
)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(stock_splits.router)
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(dividends.router, prefix="/api/v1/dividends", tags=["dividends"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

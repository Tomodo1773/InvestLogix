"""
FastAPIアプリケーション定義
ルーティングとミドルウェアの設定を行う
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import settings
from .routes import router

# FastAPIアプリケーションの作成
app = FastAPI(
    title="InvestLogix API",
    description="株式投資ポートフォリオ管理APIサービス",
    version="1.0.0",
)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # 環境変数から読み込む
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターのマウント
app.include_router(
    router,
    prefix="/api/v1",
    tags=["stocks"],
)

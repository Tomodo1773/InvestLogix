import json
from enum import Enum
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


class LogLevel(str, Enum):
    """ログレベルの定義"""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
    TRACE = "trace"


class Settings(BaseSettings):
    """アプリケーション設定"""

    # データベース設定
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "investlogix"
    DATABASE_URL: str | None = None
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # 認証設定
    JWT_SECRET_KEY: str = "dev_secret_key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # J-Quants API設定
    JQUANTS_API_KEY: str = ""

    # Alpha Vantage API設定
    ALPHAVANTAGE_API_KEY: str = ""

    # CORS設定
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # サーバー設定
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: LogLevel = LogLevel.INFO
    RELOAD: bool = True

    # SQLAlchemy URL
    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        """データベースURLを生成（URLエンコード付き）"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """CORS_ORIGINSをJSON文字列からリストに変換"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [i.strip() for i in v.split(",")]
        return v

    @field_validator("PORT", "ACCESS_TOKEN_EXPIRE_MINUTES", mode="before")
    @classmethod
    def parse_number(cls, v: str | int) -> int:
        """文字列を数値に変換"""
        if isinstance(v, str):
            return int(v)
        return v

    @field_validator("DB_ECHO", "RELOAD", mode="before")
    @classmethod
    def parse_boolean(cls, v: str | bool) -> bool:
        """文字列をブール値に変換"""
        if isinstance(v, str):
            return v.lower() == "true"
        return v

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def parse_log_level(cls, v: str) -> LogLevel:
        """ログレベル文字列をEnum値に変換"""
        try:
            return LogLevel[v.upper()]
        except KeyError:
            return LogLevel.INFO

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="allow",  # 未定義の環境変数を許可
    )


# 設定インスタンスの生成
settings = Settings()

# データベース接続設定
engine_config = {"echo": True}

# エンジンの作成時にプール設定を最適化
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URL,
    echo=settings.DB_ECHO,
    poolclass=NullPool,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)


async def get_db():
    """
    データベースセッションの依存性注入
    - 戻り値: 非同期セッション
    - 使用例: db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def set_rls_user_id(session: AsyncSession, user_id: int) -> None:
    """
    RLS用のuser_idをPostgreSQLセッション変数に設定する
    - session: データベースセッション
    - user_id: 設定するユーザーID

    NOTE:
    - asyncpgではSET文へのバインドパラメータ展開（`SET ... = $1`）が構文エラーになる。
    - `set_config` を使うと安全にバインド値を渡せる。
    """
    from sqlalchemy import text

    await session.execute(
        text("SELECT set_config('app.current_user_id', :uid, false)"),
        {"uid": str(user_id)},
    )

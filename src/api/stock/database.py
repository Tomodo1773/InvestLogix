import json
from enum import Enum
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


class LogLevel(str, Enum):
    """ログレベルの定義"""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
    TRACE = "trace"


class Environment(str, Enum):
    """環境の定義"""

    DEVELOPMENT = "development"
    DOCKER = "docker"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """アプリケーション設定"""

    # 環境設定
    ENVIRONMENT: Environment = Environment.DEVELOPMENT

    # データベース設定
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "investlogix"
    DATABASE_URL: str | None = None

    # 認証設定
    JWT_SECRET_KEY: str = "dev_secret_key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

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
        """
        環境に応じたデータベースURLを生成
        - development: SQLite
        - docker, staging, production: PostgreSQL
        """
        if self.ENVIRONMENT == Environment.DEVELOPMENT:
            return "sqlite+aiosqlite:///./dev.db"

        # Docker環境または本番環境の場合
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

    @field_validator("RELOAD", mode="before")
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

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def parse_environment(cls, v: str) -> Environment:
        """環境文字列をEnum値に変換"""
        try:
            return Environment[v.upper()]
        except KeyError:
            return Environment.DEVELOPMENT

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="allow",  # 未定義の環境変数を許可
    )


# 設定インスタンスの生成
settings = Settings()

# データベース接続設定
engine_config = {"echo": True}

# SQLite固有の設定
if settings.ENVIRONMENT == Environment.DEVELOPMENT:
    engine_config["connect_args"] = {"check_same_thread": False}

# データベースエンジンの設定
engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URL, **engine_config)

# セッションファクトリの設定
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


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

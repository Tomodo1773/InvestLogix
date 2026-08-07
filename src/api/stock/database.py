from enum import Enum

from pydantic import field_validator, model_validator
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

    # 認証設定（Cloudflare Access）
    # CF_ACCESS_TEAM_DOMAIN: Zero TrustのチームドメインでJWKSとissuerの導出に使う
    #   （例: example.cloudflareaccess.com）
    # CF_ACCESS_AUD: Access applicationのAudienceタグ。他アプリ向けJWTの使い回しを防ぐ
    # DEV_AUTH_EMAIL: Cloudflareを経由しないローカル開発でログイン扱いにするメールアドレス。
    #   productionでは設定できない（下の検証で起動時に失敗する）
    CF_ACCESS_TEAM_DOMAIN: str = ""
    CF_ACCESS_AUD: str = ""
    DEV_AUTH_EMAIL: str = ""

    # J-Quants API設定
    JQUANTS_API_KEY: str = ""

    # Alpha Vantage API設定
    ALPHAVANTAGE_API_KEY: str = ""

    # Tiingo API設定
    TIINGO_API_KEY: str = ""

    # OpenAI API設定
    OPENAI_API_KEY: str = ""

    # LINE通知設定
    LINE_CHANNEL_ACCESS_TOKEN: str = ""

    # サーバー設定
    ENVIRONMENT: str = "development"
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

    @field_validator("PORT", mode="before")
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

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @model_validator(mode="after")
    def validate_auth_settings(self) -> "Settings":
        """
        本番の認証設定に穴が空いたまま起動しないようにする
        - 開発用の認証迂回が有効なまま本番に出ることを防ぐ
        - Access の検証設定が無いと全リクエストが401になるため、起動時に気付けるようにする
        """
        if not self.is_production:
            return self

        if self.DEV_AUTH_EMAIL:
            raise ValueError("DEV_AUTH_EMAILはproductionでは設定できません")
        if not self.CF_ACCESS_TEAM_DOMAIN or not self.CF_ACCESS_AUD:
            raise ValueError("productionではCF_ACCESS_TEAM_DOMAINとCF_ACCESS_AUDが必要です")
        return self

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
            await session.commit()
        except Exception:
            await session.rollback()
            raise
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

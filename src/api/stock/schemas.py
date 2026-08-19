from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from .utils.datetime import from_jst_input, to_jst


class SecurityType(str, Enum):
    """証券種別"""

    STOCK = "STOCK"
    ETF = "ETF"
    REIT = "REIT"
    FUND = "FUND"


class TransactionType(str, Enum):
    """取引種別"""

    BUY = "buy"
    SELL = "sell"


class AccountType(str, Enum):
    """預かり種別"""

    NISA_GROWTH = "NISA(成長投資枠)"
    NISA_TSUMITATE = "NISA(つみたて投資枠)"
    JUNIOR_NISA = "ジュニアNISA"
    OLD_NISA = "旧NISA"
    SPECIFIC = "特定"


class StockBase(BaseModel):
    symbol: str
    name: str
    name_en: str | None
    market: str
    security_type: SecurityType
    currency: str


class Stock(BaseModel):
    symbol: str
    name: str
    name_en: str | None
    market: str
    security_type: SecurityType
    currency: str
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("last_updated")
    def serialize_last_updated(self, v: datetime) -> str:
        """レスポンス時: JSTに変換してISO形式で返す"""
        return to_jst(v).isoformat() if v else None


class StockJPXDetailBase(BaseModel):
    symbol: str
    sector_17_code: str | None
    sector_17_name: str | None
    sector_33_code: str | None
    sector_33_name: str | None
    market_segment: str
    market_code: str | None
    market_name: str | None
    margin_trading: bool = True


class StockJPXDetail(StockJPXDetailBase):
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("last_updated")
    def serialize_last_updated(self, v: datetime) -> str:
        """レスポンス時: JSTに変換してISO形式で返す"""
        return to_jst(v).isoformat() if v else None


class StockUSDetailBase(BaseModel):
    symbol: str
    gics_sector: str | None
    gics_industry: str | None
    sp500_component: bool = False
    market: str


class StockUSDetail(StockUSDetailBase):
    model_config = ConfigDict(from_attributes=True)


class StockSplitBase(BaseModel):
    """株式分割情報の基底スキーマ"""

    symbol: str = Field(..., min_length=1, max_length=15)
    split_date: datetime = Field(
        ...,
        json_schema_extra={"examples": ["2024-01-15T00:00:00+09:00", "2024-01-15T00:00:00", "2024-01-15"]},
    )
    split_ratio: float = Field(..., gt=0, description="分割比率（例: 4:1分割なら4.0、1:2併合なら0.5）")

    @field_validator("split_date", mode="before")
    @classmethod
    def validate_split_date(cls, v: str | datetime) -> datetime:
        """リクエスト時: naive datetime入力をJSTとして扱う"""
        return from_jst_input(v)


class StockSplitCreate(StockSplitBase):
    """株式分割登録リクエスト"""


class StockSplit(StockSplitBase):
    """株式分割情報"""

    split_id: int
    user_id: int
    created_at: datetime
    stock_name: str | None = None
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("split_date", "created_at")
    def serialize_datetime(self, v: datetime) -> str:
        """レスポンス時: JSTに変換してISO形式で返す"""
        return to_jst(v).isoformat() if v else None


class UserBase(BaseModel):
    """ユーザー登録リクエスト兼、ユーザー表現の共通項目

    認証はCloudflare Accessが行うためパスワードは持たない。
    """

    username: str
    email: str


class User(UserBase):
    user_id: int
    created_at: datetime
    slack_user_id: str | None = None
    is_admin: bool = False
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, v: datetime) -> str:
        """レスポンス時: JSTに変換してISO形式で返す"""
        return to_jst(v).isoformat() if v else None


class HoldingBase(BaseModel):
    symbol: str
    quantity: float
    average_cost: float
    total_cost: float
    current_price: float | None
    current_price_usd: float | None = None
    market_value: float | None
    market_value_usd: float | None = None
    realized_pl: float | None
    total_dividend: float | None
    unrealized_pl: float | None
    unrealized_pl_percentage: float | None
    total_pl: float | None
    total_pl_percentage: float | None
    note: str | None = None


class HoldingNoteUpdate(BaseModel):
    note: str | None = Field(None, max_length=2000)


class AccountHolding(BaseModel):
    account_type: AccountType
    quantity: float


class Holding(HoldingBase):
    user_id: int
    last_updated: datetime
    stock_name: str | None = None
    security_type: str | None = None
    currency: str | None = None
    country: str | None = None
    sector_name: str | None = None
    account_holdings: list[AccountHolding] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("last_updated")
    def serialize_last_updated(self, v: datetime) -> str:
        """レスポンス時: JSTに変換してISO形式で返す"""
        return to_jst(v).isoformat() if v else None


class TransactionBase(BaseModel):
    symbol: str
    transaction_type: TransactionType
    quantity: float
    price: float
    usd_price: float | None = None
    adjusted_price: float | None = None
    adjusted_quantity: float | None = None
    account_type: AccountType
    fee: float
    tax: float
    realized_pl: float | None = None


class Transaction(TransactionBase):
    transaction_id: int
    user_id: int
    transaction_date: datetime
    stock_name: str | None = None  # 銘柄名を追加
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("transaction_date")
    def serialize_transaction_date(self, v: datetime) -> str:
        """レスポンス時: JSTに変換してISO形式で返す"""
        return to_jst(v).isoformat() if v else None


class TransactionWithPL(Transaction):
    """買付損益情報を含む取引情報"""

    unrealized_pl: float | None = None  # 未実現損益金額（現在価格×数量 - 取得価格×数量）
    unrealized_pl_percentage: float | None = None  # 未実現損益率（%）


class PortfolioHistoryBase(BaseModel):
    date: datetime
    total_cost: float
    total_market_value: float
    total_unrealized_pl: float
    total_unrealized_pl_percentage: float
    total_realized_pl: float
    total_dividend: float
    total_pl: float
    total_pl_percentage: float

    @field_serializer("date")
    def serialize_date(self, v: datetime) -> str:
        """レスポンス時: JSTに変換してISO形式で返す"""
        return to_jst(v).isoformat() if v else None


class PortfolioHistory(PortfolioHistoryBase):
    history_id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)


class DividendBase(BaseModel):
    symbol: str
    payment_date: datetime = Field(
        ...,
        json_schema_extra={"examples": ["2024-03-15T00:00:00+09:00", "2024-03-15T00:00:00", "2024-03-15"]},
    )
    shares_owned: float
    total_amount: float
    tax: float | None
    fee: float | None

    @field_validator("payment_date", mode="before")
    @classmethod
    def validate_payment_date(cls, v: str | datetime) -> datetime:
        """リクエスト時: naive datetime入力をJSTとして扱う"""
        return from_jst_input(v)


class Dividend(DividendBase):
    dividend_id: int
    user_id: int
    stock_name: str | None = None  # 銘柄名を追加
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("payment_date")
    def serialize_payment_date(self, v: datetime) -> str:
        """レスポンス時: JSTに変換してISO形式で返す"""
        return to_jst(v).isoformat() if v else None


class PortfolioHistoryResponse(BaseModel):
    """ポートフォリオ履歴のレスポンスモデル"""

    date: datetime
    total_cost: float
    total_market_value: float
    total_unrealized_pl: float
    total_unrealized_pl_percentage: float
    total_realized_pl: float
    total_dividend: float
    total_pl: float
    total_pl_percentage: float

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("date")
    def serialize_date(self, v: datetime) -> str:
        """レスポンス時: JSTに変換してISO形式で返す"""
        return to_jst(v).isoformat() if v else None


class TotalPurchaseByAccount(BaseModel):
    """口座種別ごとの購入金額"""

    juniorNISA: float = 0.0
    oldNISA: float = 0.0
    NISAAccumulation: float = 0.0
    NISAGrowth: float = 0.0
    specific: float = 0.0


class MonthlySummary(BaseModel):
    """月次トランザクション集計のレスポンスモデル"""

    year: int
    month: int
    total_purchase: TotalPurchaseByAccount


class YearlySummary(BaseModel):
    """年次トランザクション集計のレスポンスモデル"""

    year: int
    total_purchase: TotalPurchaseByAccount


class MonthlyDividend(BaseModel):
    """月次配当集計のレスポンスモデル"""

    year: int
    month: int
    total_dividend: float


class DividendBySymbol(BaseModel):
    """銘柄別配当集計のレスポンスモデル"""

    symbol: str
    stock_name: str
    total_dividend: float


# レスポンスモデル
class StockWithRelations(Stock):
    jpx_detail: StockJPXDetail | None = None
    us_detail: StockUSDetail | None = None
    holdings: list[Holding] = []
    transactions: list[Transaction] = []
    portfolio_history: list[PortfolioHistory] = []
    dividend: list[Dividend] = []


# APIリクエスト/レスポンスモデル
class StockCreate(BaseModel):
    """株式銘柄登録リクエスト"""

    symbol: str


class StockJPXDetailCreate(StockJPXDetailBase):
    """日本株詳細情報登録リクエスト"""


class StockUSDetailCreate(StockUSDetailBase):
    """米国株詳細情報登録リクエスト"""


class TransactionCreate(BaseModel):
    """取引登録リクエスト"""

    symbol: str
    transaction_type: TransactionType
    quantity: float
    price: float
    usd_price: float | None = None
    account_type: AccountType
    fee: float
    tax: float
    transaction_date: datetime = Field(
        ...,
        json_schema_extra={"examples": ["2024-01-15T10:30:00+09:00", "2024-01-15T10:30:00", "2024-01-15"]},
    )

    @field_validator("transaction_date", mode="before")
    @classmethod
    def validate_transaction_date(cls, v: str | datetime) -> datetime:
        """リクエスト時: naive datetime入力をJSTとして扱う"""
        return from_jst_input(v)


class DividendCreate(DividendBase):
    """配当金登録リクエスト"""


class PortfolioSummary(BaseModel):
    """ポートフォリオサマリーレスポンス"""

    total_cost: float
    total_market_value: float
    total_unrealized_pl: float
    total_unrealized_pl_percentage: float
    total_realized_pl: float
    total_dividend: float
    total_pl: float
    total_pl_percentage: float
    holdings_by_market: dict[str, float]
    holdings_by_currency: dict[str, float]


class SlackUserIdUpdate(BaseModel):
    """Slack User ID更新リクエスト"""

    slack_user_id: str = Field(min_length=2, max_length=100)


# 週間騰落率通知用のスキーマ
class StockWeeklyPerformance(BaseModel):
    """週間パフォーマンス情報"""

    symbol: str
    name: str
    latest_price: float
    old_price: float
    change_rate: float  # 騰落率（%）


class WeeklyPerformanceResponse(BaseModel):
    """週間騰落率取得レスポンス（画面表示用）"""

    top_performers: list[StockWeeklyPerformance]
    bottom_performers: list[StockWeeklyPerformance]
    all_performers: list[StockWeeklyPerformance]
    timestamp: str


# 株価時系列データ用のスキーマ
class PriceDataPoint(BaseModel):
    """株価データポイント"""

    date: str = Field(..., description="日付（YYYY-MM-DD形式）")
    open: float = Field(..., description="始値")
    high: float = Field(..., description="高値")
    low: float = Field(..., description="安値")
    close: float = Field(..., description="終値")
    volume: int = Field(..., description="出来高")


class PriceHistoryInterval(str, Enum):
    """株価データの時間間隔"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class PriceHistoryResponse(BaseModel):
    """株価履歴レスポンス"""

    symbol: str = Field(..., description="銘柄コード")
    interval: str = Field(..., description="データ間隔（daily, weekly, monthly）")
    data: list[PriceDataPoint] = Field(..., description="株価データのリスト")


# CSVインポート用のスキーマ
class CsvTransactionPreview(BaseModel):
    """CSVから解析された取引データ（プレビュー用）"""

    symbol: str
    name: str
    transaction_type: TransactionType
    quantity: float
    price: float
    usd_price: float | None = None
    account_type: AccountType
    fee: float
    tax: float
    transaction_date: datetime

    @field_serializer("transaction_date")
    def serialize_transaction_date(self, v: datetime) -> str:
        """レスポンス時: JSTに変換してISO形式で返す"""
        return to_jst(v).isoformat() if v else None


class ImportPreviewResponse(BaseModel):
    """インポートプレビューレスポンス"""

    new_transactions: list[CsvTransactionPreview]
    existing_count: int
    csv_total_count: int
    skipped_count: int
    errors: list[str]


class ImportConfirmRequest(BaseModel):
    """インポート確認リクエスト"""

    transactions: list[TransactionCreate]


class ImportConfirmResponse(BaseModel):
    """インポート確認レスポンス"""

    created_count: int
    failed_count: int
    errors: list[str]


# 配当金CSVインポート用のスキーマ
class CsvDividendPreview(BaseModel):
    """CSVから解析された配当金データ（プレビュー用）"""

    symbol: str
    name: str
    payment_date: datetime
    shares_owned: float
    total_amount: float

    @field_serializer("payment_date")
    def serialize_payment_date(self, v: datetime) -> str:
        """レスポンス時: JSTに変換してISO形式で返す"""
        return to_jst(v).isoformat() if v else None


class DividendImportPreviewResponse(BaseModel):
    """配当金インポートプレビューレスポンス"""

    new_dividends: list[CsvDividendPreview]
    existing_count: int
    csv_total_count: int
    skipped_count: int
    errors: list[str]


class DividendImportConfirmRequest(BaseModel):
    """配当金インポート確認リクエスト"""

    dividends: list[DividendCreate]


class DividendImportConfirmResponse(BaseModel):
    """配当金インポート確認レスポンス"""

    created_count: int
    failed_count: int
    errors: list[str]

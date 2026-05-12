from datetime import datetime
from enum import Enum
from typing import List, Optional

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
    name_en: Optional[str]
    market: str
    security_type: SecurityType
    currency: str


class Stock(BaseModel):
    symbol: str
    name: str
    name_en: Optional[str]
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
    sector_17_code: Optional[str]
    sector_17_name: Optional[str]
    sector_33_code: Optional[str]
    sector_33_name: Optional[str]
    market_segment: str
    market_code: Optional[str]
    market_name: Optional[str]
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
    gics_sector: Optional[str]
    gics_industry: Optional[str]
    sp500_component: bool = False
    market: str


class StockUSDetail(StockUSDetailBase):
    model_config = ConfigDict(from_attributes=True)


class StockSplitBase(BaseModel):
    """株式分割情報の基底スキーマ"""

    symbol: str
    split_date: datetime = Field(
        ...,
        json_schema_extra={"examples": ["2024-01-15T00:00:00+09:00", "2024-01-15T00:00:00", "2024-01-15"]},
    )
    split_ratio: float = Field(..., description="分割比率（例: 4:1分割なら4.0、1:2併合なら0.5）")

    @field_validator("split_date", mode="before")
    @classmethod
    def validate_split_date(cls, v: str | datetime) -> datetime:
        """リクエスト時: naive datetime入力をJSTとして扱う"""
        return from_jst_input(v)


class StockSplitCreate(StockSplitBase):
    """株式分割登録リクエスト"""

    pass


class StockSplit(StockSplitBase):
    """株式分割情報"""

    split_id: int
    user_id: int
    created_at: datetime
    stock_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("split_date", "created_at")
    def serialize_datetime(self, v: datetime) -> str:
        """レスポンス時: JSTに変換してISO形式で返す"""
        return to_jst(v).isoformat() if v else None


class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    user_id: int
    created_at: datetime
    line_user_id: Optional[str] = None
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
    current_price: Optional[float]
    market_value: Optional[float]
    realized_pl: Optional[float]
    total_dividend: Optional[float]
    unrealized_pl: Optional[float]
    unrealized_pl_percentage: Optional[float]
    total_pl: Optional[float]
    total_pl_percentage: Optional[float]
    note: Optional[str] = None


class HoldingNoteUpdate(BaseModel):
    note: Optional[str] = Field(None, max_length=2000)


class Holding(HoldingBase):
    user_id: int
    last_updated: datetime
    stock_name: Optional[str] = None
    security_type: Optional[str] = None
    currency: Optional[str] = None
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
    usd_price: Optional[float] = None
    adjusted_price: Optional[float] = None
    adjusted_quantity: Optional[float] = None
    account_type: AccountType
    fee: float
    tax: float
    realized_pl: Optional[float] = None


class Transaction(TransactionBase):
    transaction_id: int
    user_id: int
    transaction_date: datetime
    stock_name: Optional[str] = None  # 銘柄名を追加
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("transaction_date")
    def serialize_transaction_date(self, v: datetime) -> str:
        """レスポンス時: JSTに変換してISO形式で返す"""
        return to_jst(v).isoformat() if v else None


class TransactionWithPL(Transaction):
    """買付損益情報を含む取引情報"""

    unrealized_pl: Optional[float] = None  # 未実現損益金額（現在価格×数量 - 取得価格×数量）
    unrealized_pl_percentage: Optional[float] = None  # 未実現損益率（%）


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
    tax: Optional[float]
    fee: Optional[float]

    @field_validator("payment_date", mode="before")
    @classmethod
    def validate_payment_date(cls, v: str | datetime) -> datetime:
        """リクエスト時: naive datetime入力をJSTとして扱う"""
        return from_jst_input(v)


class Dividend(DividendBase):
    dividend_id: int
    user_id: int
    stock_name: Optional[str] = None  # 銘柄名を追加
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


# レスポンスモデル
class StockWithRelations(Stock):
    jpx_detail: Optional[StockJPXDetail] = None
    us_detail: Optional[StockUSDetail] = None
    holdings: List[Holding] = []
    transactions: List[Transaction] = []
    portfolio_history: List[PortfolioHistory] = []
    dividend: List[Dividend] = []


class UserWithRelations(User):
    holdings: List[Holding] = []
    transactions: List[Transaction] = []
    portfolio_history: List[PortfolioHistory] = []
    dividend: List[Dividend] = []


# APIリクエスト/レスポンスモデル
class Token(BaseModel):
    """JWTトークンレスポンス"""

    access_token: str
    token_type: str = "bearer"


class StockCreate(BaseModel):
    """株式銘柄登録リクエスト"""

    symbol: str


class StockJPXDetailCreate(StockJPXDetailBase):
    """日本株詳細情報登録リクエスト"""

    pass


class StockUSDetailCreate(StockUSDetailBase):
    """米国株詳細情報登録リクエスト"""

    pass


class TransactionCreate(BaseModel):
    """取引登録リクエスト"""

    symbol: str
    transaction_type: TransactionType
    quantity: float
    price: float
    usd_price: Optional[float] = None
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

    pass


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


class LoginRequest(BaseModel):
    """ログインリクエスト用のスキーマ"""

    username: str
    password: str


# LINE UserID登録用のスキーマを追加
class LineUserIdUpdate(BaseModel):
    """LINE UserID更新リクエスト"""

    line_user_id: str


# 週間騰落率通知用のスキーマ
class StockWeeklyPerformance(BaseModel):
    """週間パフォーマンス情報"""

    symbol: str
    name: str
    latest_price: float
    old_price: float
    change_rate: float  # 騰落率（%）


class WeeklyPerformanceNotifyResponse(BaseModel):
    """週間騰落率通知レスポンス"""

    top_performers: List[StockWeeklyPerformance]
    bottom_performers: List[StockWeeklyPerformance]
    notification_sent: bool
    timestamp: str


class WeeklyPerformanceResponse(BaseModel):
    """週間騰落率取得レスポンス（画面表示用）"""

    top_performers: List[StockWeeklyPerformance]
    bottom_performers: List[StockWeeklyPerformance]
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
    data: List[PriceDataPoint] = Field(..., description="株価データのリスト")


# CSVインポート用のスキーマ
class CsvTransactionPreview(BaseModel):
    """CSVから解析された取引データ（プレビュー用）"""

    symbol: str
    name: str
    transaction_type: TransactionType
    quantity: float
    price: float
    usd_price: Optional[float] = None
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

    new_transactions: List[CsvTransactionPreview]
    existing_count: int
    csv_total_count: int
    skipped_count: int
    errors: List[str]


class ImportConfirmRequest(BaseModel):
    """インポート確認リクエスト"""

    transactions: List[TransactionCreate]


class ImportConfirmResponse(BaseModel):
    """インポート確認レスポンス"""

    created_count: int
    failed_count: int
    errors: List[str]


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

    new_dividends: List[CsvDividendPreview]
    existing_count: int
    csv_total_count: int
    skipped_count: int
    errors: List[str]


class DividendImportConfirmRequest(BaseModel):
    """配当金インポート確認リクエスト"""

    dividends: List[DividendCreate]


class DividendImportConfirmResponse(BaseModel):
    """配当金インポート確認レスポンス"""

    created_count: int
    failed_count: int
    errors: List[str]

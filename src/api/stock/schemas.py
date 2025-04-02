from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


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

    JUNIOR_NISA = "ジュニアNISA"
    OLD_NISA = "旧NISA"
    NISA_TSUMITATE = "NISA(つみたて投資枠)"
    NISA_GROWTH = "NISA(成長投資枠)"
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


class StockUSDetailBase(BaseModel):
    symbol: str
    gics_sector: Optional[str]
    gics_industry: Optional[str]
    sp500_component: bool = False
    market: str


class StockUSDetail(StockUSDetailBase):
    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    user_id: int
    created_at: datetime
    line_user_id: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class HoldingBase(BaseModel):
    symbol: str
    quantity: Decimal
    average_cost: Decimal
    total_cost: Decimal
    current_price: Optional[Decimal]
    market_value: Optional[Decimal]
    realized_pl: Optional[Decimal]
    total_dividend: Optional[Decimal]
    unrealized_pl: Optional[Decimal]
    unrealized_pl_percentage: Optional[Decimal]


class Holding(HoldingBase):
    user_id: int
    last_updated: datetime
    stock_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class TransactionBase(BaseModel):
    symbol: str
    transaction_type: TransactionType
    quantity: Decimal
    price: Decimal
    usd_price: Optional[Decimal] = None
    adjusted_price: Optional[Decimal] = None
    account_type: AccountType
    fee: Decimal
    tax: Decimal
    realized_pl: Optional[Decimal] = None


class Transaction(TransactionBase):
    transaction_id: int
    user_id: int
    transaction_date: datetime
    stock_name: Optional[str] = None  # 銘柄名を追加
    current_price: Optional[Decimal] = None  # 現在価格を追加
    model_config = ConfigDict(from_attributes=True)


class PortfolioHistoryBase(BaseModel):
    date: datetime
    total_cost: Decimal
    total_market_value: Decimal
    total_unrealized_pl: Decimal
    total_unrealized_pl_percentage: Decimal
    total_realized_pl: Decimal
    total_dividend: Decimal


class PortfolioHistory(PortfolioHistoryBase):
    history_id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)


class DividendBase(BaseModel):
    symbol: str
    payment_date: datetime
    shares_owned: Decimal
    total_amount: Decimal
    tax: Optional[Decimal]
    fee: Optional[Decimal]


class Dividend(DividendBase):
    dividend_id: int
    user_id: int
    stock_name: Optional[str] = None  # 銘柄名を追加
    model_config = ConfigDict(from_attributes=True)


class PortfolioHistoryResponse(BaseModel):
    """ポートフォリオ履歴のレスポンスモデル"""

    date: datetime
    total_cost: float
    total_market_value: float
    total_unrealized_pl: float
    total_unrealized_pl_percentage: float
    total_realized_pl: float
    total_dividend: float

    class Config:
        from_attributes = True


class MonthlySummary(BaseModel):
    """月次トランザクション集計のレスポンスモデル"""

    year: int
    month: int
    total_purchase: dict[str, float]


class YearlySummary(BaseModel):
    """年次トランザクション集計のレスポンスモデル"""

    year: int
    total_purchase: dict[str, float]


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


class TokenData(BaseModel):
    """JWTトークンデータ"""

    username: str | None = None


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
    quantity: Decimal
    price: Decimal
    usd_price: Optional[Decimal] = None
    adjusted_price: Optional[Decimal] = None
    account_type: AccountType
    fee: Decimal
    tax: Decimal
    transaction_date: datetime


class DividendCreate(DividendBase):
    """配当金登録リクエスト"""

    pass


class PortfolioSummary(BaseModel):
    """ポートフォリオサマリーレスポンス"""

    total_cost: Decimal
    total_market_value: Decimal
    total_unrealized_pl: Decimal
    total_unrealized_pl_percentage: Decimal
    total_realized_pl: Decimal
    total_dividend: Decimal
    holdings_by_market: dict[str, Decimal]
    holdings_by_currency: dict[str, Decimal]


class LoginRequest(BaseModel):
    """ログインリクエスト用のスキーマ"""

    username: str
    password: str


# LINE UserID登録用のスキーマを追加
class LineUserIdUpdate(BaseModel):
    """LINE UserID更新リクエスト"""

    line_user_id: str

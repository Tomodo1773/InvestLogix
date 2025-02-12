from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class StockBase(BaseModel):
    symbol: str
    name: str
    name_en: Optional[str]
    market: str
    security_type: str
    currency: str


class Stock(BaseModel):
    symbol: str
    name: str
    name_en: Optional[str]
    market: str
    security_type: str
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
    model_config = ConfigDict(from_attributes=True)


class HoldingBase(BaseModel):
    symbol: str
    quantity: Decimal
    average_cost: Decimal
    total_cost: Decimal
    current_price: Optional[Decimal]
    market_value: Optional[Decimal]
    unrealized_pl: Optional[Decimal]
    unrealized_pl_percentage: Optional[Decimal]


class Holding(HoldingBase):
    holding_id: int
    user_id: int
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)


class TransactionBase(BaseModel):
    symbol: str
    transaction_type: str
    quantity: Decimal
    price: Decimal
    account_type: str
    fee: Decimal
    tax: Decimal


class Transaction(TransactionBase):
    transaction_id: int
    user_id: int
    transaction_date: datetime
    model_config = ConfigDict(from_attributes=True)


class PortfolioHistoryBase(BaseModel):
    date: datetime
    total_cost: Decimal
    total_market_value: Decimal
    total_unrealized_pl: Decimal
    total_unrealized_pl_percentage: Decimal
    total_realized_pl: Decimal
    total_dividend: Decimal
    cash_balance: Decimal


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
    model_config = ConfigDict(from_attributes=True)


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


class TransactionCreate(TransactionBase):
    """取引登録リクエスト"""

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
    cash_balance: Decimal
    holdings_by_market: dict[str, Decimal]
    holdings_by_currency: dict[str, Decimal]


class LoginRequest(BaseModel):
    """ログインリクエスト"""

    username: str
    password: str

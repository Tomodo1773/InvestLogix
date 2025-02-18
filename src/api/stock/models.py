from datetime import datetime
from decimal import Decimal

import pytz
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship

# JSTタイムゾーンを定義
JST = pytz.timezone("Asia/Tokyo")


def get_jst_now():
    """現在の日本時間を返す"""
    return datetime.now(JST)


class Base(DeclarativeBase):
    pass


class Stock(Base):
    """
    基本情報のみを保持する既存テーブル
    """

    __tablename__ = "stocks"

    symbol = Column(String(10), primary_key=True)  # [SYSTEM] 銘柄コード (例: "AAPL")
    name = Column(String(100), nullable=False)  # [API_FETCH] 銘柄名 (例: "Apple Inc.")
    name_en = Column(String(100))  # [API_FETCH] 英語名 (例: "Apple Inc.")
    market = Column(String(20), nullable=False)  # [API_FETCH] 上場市場 (例: "JPX", "NYSE", "NASDAQ")
    security_type = Column(
        Enum("STOCK", "ETF", "REIT", "FUND", name="security_types"), nullable=False
    )  # [SYSTEM] 証券種別 (例: "STOCK")
    currency = Column(String(3), nullable=False)  # [SYSTEM] 通貨 (例: "USD", "JPY")
    last_updated = Column(DateTime, default=get_jst_now, onupdate=get_jst_now)  # [SYSTEM] 最終更新日時（JST）

    holdings = relationship("Holding", back_populates="stock")  # Holding モデルとの関連
    transactions = relationship("Transaction", back_populates="stock")  # Transaction モデルとの関連
    dividend = relationship("Dividend", back_populates="stock")  # Dividend モデルとの関連
    jpx_detail = relationship("StockJPXDetail", back_populates="stock", uselist=False)  # StockJPXDetail モデルとの関連
    us_detail = relationship("StockUSDetail", back_populates="stock", uselist=False)  # StockUSDetail モデルとの関連


class StockJPXDetail(Base):
    """
    日本株の詳細情報を管理するテーブル
    """

    __tablename__ = "stock_jpx_details"

    symbol = Column(String(10), ForeignKey("stocks.symbol"), primary_key=True)  # [SYSTEM] 銘柄コード (例: "86970.T")
    sector_17_code = Column(String(2))  # [API_FETCH] 17業種区分コード (例: "16")
    sector_17_name = Column(String(50))  # [API_FETCH] 17業種区分名 (例: "金融（除く銀行）")
    sector_33_code = Column(String(4))  # [API_FETCH] 33業種区分コード (例: "7200")
    sector_33_name = Column(String(50))  # [API_FETCH] 33業種区分名 (例: "その他金融業")
    market_segment = Column(String(20), nullable=False)  # [API_FETCH] 市場区分 (プライム/スタンダード/グロース)
    market_code = Column(String(20))  # [API_FETCH] 規模区分 (例: "TOPIX Large70")
    market_name = Column(String(50))  # [API_FETCH] 規模区分名
    margin_trading = Column(Boolean, default=True)  # [API_FETCH] 信用取引可能か
    last_updated = Column(DateTime, default=get_jst_now, onupdate=get_jst_now)  # [SYSTEM] データの最終更新日時（JST）

    stock = relationship("Stock", back_populates="jpx_detail")  # Stock モデルとの関連


class StockUSDetail(Base):
    """
    米国株の追加情報
    """

    __tablename__ = "stock_us_details"

    symbol = Column(String(10), ForeignKey("stocks.symbol"), primary_key=True)  # [SYSTEM] 銘柄コード
    gics_sector = Column(String(50))  # [API_FETCH] GICSセクター
    gics_industry = Column(String(50))  # [API_FETCH] GICS業種
    sp500_component = Column(Boolean, default=False)  # [API_FETCH] S&P500構成銘柄か
    market = Column(String(20), nullable=False)  # [API_FETCH] 市場情報

    stock = relationship("Stock", back_populates="us_detail")


class User(Base):
    """
    user_id: ユーザーID
    username: ユーザー名
    email: メールアドレス
    password_hash: パスワードのハッシュ値
    created_at: 登録日時
    """

    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)  # [SYSTEM] ユーザーID
    username = Column(String(50), unique=True, nullable=False)  # [USER_INPUT] ユーザー名
    email = Column(String(100), unique=True, nullable=False)  # [USER_INPUT] メールアドレス
    password_hash = Column(String(255), nullable=False)  # [SYSTEM] パスワードのハッシュ値
    created_at = Column(DateTime, default=get_jst_now)  # [SYSTEM] 登録日時（JST）

    holdings = relationship("Holding", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    dividend = relationship("Dividend", back_populates="user")
    portfolio_history = relationship("PortfolioHistory", back_populates="user")


class Holding(Base):
    """
    保有銘柄の情報と損益状況を管理するテーブル
    """

    __tablename__ = "holdings"

    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)  # [SYSTEM] ユーザーID
    symbol = Column(String(10), ForeignKey("stocks.symbol"), primary_key=True)  # [SYSTEM] 銘柄コード

    # 保有情報
    quantity = Column(Numeric(10, 2), nullable=False)  # [AUTO_CALC] 保有数量
    average_cost = Column(Numeric(10, 2), nullable=False)  # [AUTO_CALC] 平均取得単価（取得価格合計 / 保有数量）
    total_cost = Column(Numeric(10, 2), nullable=False)  # [AUTO_CALC] 取得価格合計（Transactionから取得）

    # 現在値情報
    current_price = Column(Numeric(10, 2))  # [API_FETCH] 現在価格
    market_value = Column(Numeric(10, 2))  # [AUTO_CALC] 時価評価額（現在価格 * 保有数量）
    realized_pl = Column(Numeric(10, 2), default=Decimal("0"))  # [AUTO_CALC] 売却益（（平均取得単価 - 現在価格） * 保有数量）
    total_dividend = Column(Numeric(10, 2), default=Decimal("0"))  # [AUTO_CALC] 配当総額
    unrealized_pl = Column(Numeric(10, 2))  # [AUTO_CALC] 評価損益（時価評価額 + 売却益 + 配当総額 - 取得価格合計）
    unrealized_pl_percentage = Column(Numeric(5, 2))  # [AUTO_CALC] 評価損益率（評価損益 / 取得価格合計）
    last_updated = Column(DateTime, default=get_jst_now, onupdate=get_jst_now)  # [SYSTEM] 最終更新日時（JST）

    user = relationship("User", back_populates="holdings")
    stock = relationship("Stock", back_populates="holdings")

    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_user_symbol"),)


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(Integer, primary_key=True)  # [SYSTEM] トランザクションID
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)  # [SYSTEM] ユーザーID
    symbol = Column(String(10), ForeignKey("stocks.symbol"), nullable=False)  # [USER_INPUT] 銘柄コード
    transaction_type = Column(
        Enum("buy", "sell", name="transaction_types"), nullable=False
    )  # [USER_INPUT] トランザクションタイプ (例: "buy", "sell")
    quantity = Column(Numeric(10, 2), nullable=False)  # [USER_INPUT] 数量
    price = Column(Numeric(10, 2), nullable=False)  # [USER_INPUT] 価格（日本円）
    usd_price = Column(Numeric(10, 2))  # [USER_INPUT] 米国株のドル建て価格（API取得値など）
    adjusted_price = Column(Numeric(10, 2))  # [AUTO_CALC] 株式分割による調整後の価格
    transaction_date = Column(DateTime, default=get_jst_now)  # [USER_INPUT] トランザクション日時（JST）
    account_type = Column(
        Enum("ジュニアNISA", "旧NISA", "NISA(つみたて投資枠)", "NISA(成長投資枠)", name="account_types"), nullable=False
    )  # [USER_INPUT] 預かり種別
    fee = Column(Numeric(10, 2), nullable=False)  # [USER_INPUT] 手数料
    tax = Column(Numeric(10, 2), nullable=False)  # [USER_INPUT] 税金

    user = relationship("User", back_populates="transactions")
    stock = relationship("Stock", back_populates="transactions")


class PortfolioHistory(Base):
    """
    ポートフォリオ全体の資産推移履歴
    """

    __tablename__ = "portfolio_history"

    history_id = Column(Integer, primary_key=True)  # [SYSTEM] 履歴ID
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)  # [SYSTEM] ユーザーID
    date = Column(DateTime, nullable=False)  # [SYSTEM] 記録日時
    total_cost = Column(Numeric(10, 2), nullable=False)  # [AUTO_CALC] 取得価額合計（
    total_market_value = Column(Numeric(10, 2), nullable=False)  # [AUTO_CALC] 時価評価額合計
    total_unrealized_pl = Column(Numeric(10, 2), nullable=False)  # [AUTO_CALC] 評価損益合計
    total_unrealized_pl_percentage = Column(Numeric(5, 2), nullable=False)  # [AUTO_CALC] 評価損益率
    total_realized_pl = Column(Numeric(10, 2), nullable=False)  # [AUTO_CALC] 実現損益合計
    total_dividend = Column(Numeric(10, 2), nullable=False)  # [AUTO_CALC] 配当金合計

    user = relationship("User", back_populates="portfolio_history")

    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_user_date_portfolio"),)


class Dividend(Base):
    __tablename__ = "dividend"

    dividend_id = Column(Integer, primary_key=True)  # [SYSTEM] 配当ID
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)  # [SYSTEM] ユーザーID
    symbol = Column(String(10), ForeignKey("stocks.symbol"), nullable=False)  # [USER_INPUT] 銘柄コード
    payment_date = Column(DateTime, nullable=False)  # [USER_INPUT] 支払日
    shares_owned = Column(Numeric(10, 2), nullable=False)  # [AUTO_CALC] 保有株数
    total_amount = Column(Numeric(10, 2), nullable=False)  # [USER_INPUT] 配当金総額
    tax = Column(Numeric(10, 2))  # [USER_INPUT] 税金
    fee = Column(Numeric(10, 2))  # [USER_INPUT] 手数料

    user = relationship("User", back_populates="dividend")
    stock = relationship("Stock", back_populates="dividend")

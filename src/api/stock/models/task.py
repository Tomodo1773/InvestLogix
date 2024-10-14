from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import pytz

Base = declarative_base()


def get_japan_time():
    return datetime.now(pytz.timezone("Asia/Tokyo"))


# 銘柄テーブル
class Stock(Base):
    __tablename__ = "stocks"

    symbol = Column(String(10), primary_key=True)  # 証券コード
    name = Column(String(100), nullable=False)  # 会社名（日本語）
    exchange = Column(String(20))  # 取引所
    last_updated = Column(DateTime, default=get_japan_time, onupdate=get_japan_time)  # 最終更新日時

    company_name_english = Column(String(100))  # 会社名（英語）
    sector17_code = Column(String(2))  # 17業種コード
    sector17_name = Column(String(50))  # 17業種名
    sector33_code = Column(String(4))  # 33業種コード
    sector33_name = Column(String(50))  # 33業種名
    scale_category = Column(String(20))  # 規模区分
    market_code = Column(String(4))  # 市場コード
    market_name = Column(String(20))  # 市場名
    margin_code = Column(String(1))  # 信用取引コード
    margin_name = Column(String(10))  # 信用取引区分名

    holdings = relationship("Holding", back_populates="stock")
    transactions = relationship("Transaction", back_populates="stock")
    favorites = relationship("Favorite", back_populates="stock")


# ユーザーテーブル
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=get_japan_time)

    holdings = relationship("Holding", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    favorites = relationship("Favorite", back_populates="user")

# 保有テーブル
class Holding(Base):
    __tablename__ = "holdings"

    holding_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    symbol = Column(String(10), ForeignKey("stocks.symbol"), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    average_cost = Column(Numeric(10, 2), nullable=False)

    user = relationship("User", back_populates="holdings")
    stock = relationship("Stock", back_populates="holdings")

    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_user_symbol"),)

# 取引テーブル
class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    symbol = Column(String(10), ForeignKey("stocks.symbol"), nullable=False)
    transaction_type = Column(Enum("buy", "sell", name="transaction_types"), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    transaction_date = Column(DateTime, default=get_japan_time)

    user = relationship("User", back_populates="transactions")
    stock = relationship("Stock", back_populates="transactions")

# お気に入りテーブル
class Favorite(Base):
    __tablename__ = "favorites"

    favorite_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    symbol = Column(String(10), ForeignKey("stocks.symbol"), nullable=False)
    added_at = Column(DateTime, default=get_japan_time)

    user = relationship("User", back_populates="favorites")
    stock = relationship("Stock", back_populates="favorites")

    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_user_favorite_symbol"),)

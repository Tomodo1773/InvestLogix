from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Stock(Base):
    __tablename__ = "stocks"

    symbol = Column(String(10), primary_key=True)
    name = Column(String(100), nullable=False)
    exchange = Column(String(20))
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    holdings = relationship("Holding", back_populates="stock")
    transactions = relationship("Transaction", back_populates="stock")
    favorites = relationship("Favorite", back_populates="stock")
    profit_loss_history = relationship("ProfitLossHistory", back_populates="stock")
    dividend = relationship("Dividend", back_populates="stock")


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    holdings = relationship("Holding", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    favorites = relationship("Favorite", back_populates="user")
    profit_loss_history = relationship("ProfitLossHistory", back_populates="user")
    dividend = relationship("Dividend", back_populates="user")


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


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    symbol = Column(String(10), ForeignKey("stocks.symbol"), nullable=False)
    transaction_type = Column(Enum("buy", "sell", name="transaction_types"), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    transaction_date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")
    stock = relationship("Stock", back_populates="transactions")


class Favorite(Base):
    __tablename__ = "favorites"

    favorite_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    symbol = Column(String(10), ForeignKey("stocks.symbol"), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")
    stock = relationship("Stock", back_populates="favorites")

    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_user_favorite_symbol"),)


class ProfitLossHistory(Base):
    __tablename__ = "profit_loss_history"

    history_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    symbol = Column(String(10), ForeignKey("stocks.symbol"), nullable=False)
    date = Column(DateTime, nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    current_price = Column(Numeric(10, 2), nullable=False)
    total_cost = Column(Numeric(10, 2), nullable=False)
    market_value = Column(Numeric(10, 2), nullable=False)
    unrealized_pl = Column(Numeric(10, 2), nullable=False)
    unrealized_pl_percentage = Column(Numeric(5, 2), nullable=False)

    user = relationship("User", back_populates="profit_loss_history")
    stock = relationship("Stock", back_populates="profit_loss_history")


class Dividend(Base):
    __tablename__ = "dividend"

    dividend_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    symbol = Column(String(10), ForeignKey("stocks.symbol"), nullable=False)
    ex_dividend_date = Column(DateTime, nullable=False)
    payment_date = Column(DateTime, nullable=False)
    amount_per_share = Column(Numeric(10, 4), nullable=False)
    shares_owned = Column(Numeric(10, 2), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    tax_amount = Column(Numeric(10, 2))
    exchange_rate = Column(Numeric(10, 4))
    net_amount_local_currency = Column(Numeric(10, 2))

    user = relationship("User", back_populates="dividend")
    stock = relationship("Stock", back_populates="dividend")

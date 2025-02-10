from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas
from .auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
)
from .database import get_db

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# 認証関連のエンドポイント
@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    """
    ユーザー認証を行い、JWTトークンを発行する
    - form_data: ユーザー名とパスワード
    - 認証成功時: JWTトークンを返却
    - 認証失敗時: 401 Unauthorized
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    新規ユーザーを登録する
    - user: ユーザー情報（ユーザー名、メールアドレス、パスワード）
    - 登録成功時: 作成されたユーザー情報を返却
    - ユーザー名/メールアドレス重複時: 400 Bad Request
    """
    db_user = db.query(models.User).filter((models.User.username == user.username) | (models.User.email == user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    hashed_password = get_password_hash(user.password)
    db_user = models.User(username=user.username, email=user.email, password_hash=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# 銘柄情報関連のエンドポイント
@router.post("/stocks/", response_model=schemas.Stock)
def create_stock(
    stock: schemas.StockCreate, current_user: Annotated[schemas.User, Depends(get_current_user)], db: Session = Depends(get_db)
):
    """
    新規銘柄を登録する（管理者用）
    - stock: 銘柄情報
    - 登録成功時: 作成された銘柄情報を返却
    - 銘柄コード重複時: 400 Bad Request
    """
    db_stock = db.query(models.Stock).filter(models.Stock.symbol == stock.symbol).first()
    if db_stock:
        raise HTTPException(status_code=400, detail="Symbol already registered")

    db_stock = models.Stock(**stock.model_dump())
    db.add(db_stock)
    db.commit()
    db.refresh(db_stock)
    return db_stock


@router.get("/stocks/", response_model=List[schemas.StockWithRelations])
def list_stocks(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    market: schemas.StockMarket | None = None,
    db: Session = Depends(get_db),
):
    """
    銘柄一覧を取得する
    - market: 市場でフィルタリング（オプション）
    - return: 銘柄情報のリスト（詳細情報付き）
    """
    query = db.query(models.Stock)
    if market:
        query = query.filter(models.Stock.market == market)
    return query.all()


# 取引関連のエンドポイント
@router.post("/transactions/", response_model=schemas.Transaction)
def create_transaction(
    transaction: schemas.TransactionCreate,
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    新規取引を登録する
    - transaction: 取引情報
    - 登録成功時: 作成された取引情報を返却
    - 株式が存在しない場合: 404 Not Found
    """
    # 株式の存在確認
    stock = db.query(models.Stock).filter(models.Stock.symbol == transaction.symbol).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    # 取引情報の登録
    db_transaction = models.Transaction(**transaction.model_dump(), user_id=current_user.user_id)
    db.add(db_transaction)

    # 保有情報の更新
    holding = (
        db.query(models.Holding)
        .filter(models.Holding.user_id == current_user.user_id, models.Holding.symbol == transaction.symbol)
        .first()
    )

    if transaction.transaction_type == "buy":
        if holding:
            # 既存の保有がある場合は更新
            new_quantity = holding.quantity + transaction.quantity
            new_total_cost = holding.total_cost + (transaction.quantity * transaction.price)
            holding.quantity = new_quantity
            holding.total_cost = new_total_cost
            holding.average_cost = new_total_cost / new_quantity
        else:
            # 新規保有の作成
            holding = models.Holding(
                user_id=current_user.user_id,
                symbol=transaction.symbol,
                quantity=transaction.quantity,
                average_cost=transaction.price,
                total_cost=transaction.quantity * transaction.price,
            )
            db.add(holding)

    elif transaction.transaction_type == "sell":
        if not holding or holding.quantity < transaction.quantity:
            raise HTTPException(status_code=400, detail="Insufficient shares")

        # 売却による保有数量の更新
        holding.quantity -= transaction.quantity
        if holding.quantity == 0:
            db.delete(holding)
        else:
            # 総コストを減らす（平均取得単価は変更しない）
            holding.total_cost = holding.average_cost * holding.quantity

    db.commit()
    return db_transaction


@router.get("/transactions/", response_model=List[schemas.Transaction])
def list_transactions(current_user: Annotated[schemas.User, Depends(get_current_user)], db: Session = Depends(get_db)):
    """
    ユーザーの取引履歴を取得する
    - return: 取引履歴のリスト
    """
    return (
        db.query(models.Transaction)
        .filter(models.Transaction.user_id == current_user.user_id)
        .order_by(models.Transaction.transaction_date.desc())
        .all()
    )


# ポートフォリオ関連のエンドポイント
@router.get("/portfolio/summary", response_model=schemas.PortfolioSummary)
def get_portfolio_summary(current_user: Annotated[schemas.User, Depends(get_current_user)], db: Session = Depends(get_db)):
    """
    ポートフォリオのサマリー情報を取得する
    - return: ポートフォリオの集計情報
    """
    # 保有銘柄の集計
    holdings = db.query(models.Holding).filter(models.Holding.user_id == current_user.user_id).all()

    # 市場別、通貨別の保有額集計
    holdings_by_market = {}
    holdings_by_currency = {}
    total_market_value = 0
    total_cost = 0

    for holding in holdings:
        stock = db.query(models.Stock).filter(models.Stock.symbol == holding.symbol).first()
        market_value = holding.market_value or 0

        # 市場別集計
        holdings_by_market[stock.market] = holdings_by_market.get(stock.market, 0) + market_value

        # 通貨別集計
        holdings_by_currency[stock.currency] = holdings_by_currency.get(stock.currency, 0) + market_value

        total_market_value += market_value
        total_cost += holding.total_cost

    # 配当総額の集計
    total_dividend = (
        db.query(models.Dividend)
        .filter(models.Dividend.user_id == current_user.user_id)
        .with_entities(func.sum(models.Dividend.total_amount))
        .scalar()
        or 0
    )

    return schemas.PortfolioSummary(
        total_cost=total_cost,
        total_market_value=total_market_value,
        total_unrealized_pl=total_market_value - total_cost,
        total_unrealized_pl_percentage=(total_market_value - total_cost) / total_cost * 100 if total_cost > 0 else 0,
        total_realized_pl=0,  # TODO: 実現損益の計算を実装
        total_dividend=total_dividend,
        cash_balance=0,  # TODO: 現金残高の計算を実装
        holdings_by_market=holdings_by_market,
        holdings_by_currency=holdings_by_currency,
    )


@router.get("/holdings/", response_model=List[schemas.Holding])
def list_holdings(current_user: Annotated[schemas.User, Depends(get_current_user)], db: Session = Depends(get_db)):
    """
    保有銘柄一覧を取得する
    - return: 保有銘柄のリスト
    """
    return db.query(models.Holding).filter(models.Holding.user_id == current_user.user_id).all()


# 配当関連のエンドポイント
@router.post("/dividends/", response_model=schemas.Dividend)
def create_dividend(
    dividend: schemas.DividendCreate,
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    配当情報を登録する
    - dividend: 配当情報
    - 登録成功時: 作成された配当情報を返却
    - 株式が存在しない場合: 404 Not Found
    """
    # 株式の存在確認
    stock = db.query(models.Stock).filter(models.Stock.symbol == dividend.symbol).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    db_dividend = models.Dividend(**dividend.model_dump(), user_id=current_user.user_id)
    db.add(db_dividend)
    db.commit()
    db.refresh(db_dividend)
    return db_dividend


@router.get("/dividends/", response_model=List[schemas.Dividend])
def list_dividends(current_user: Annotated[schemas.User, Depends(get_current_user)], db: Session = Depends(get_db)):
    """
    配当履歴を取得する
    - return: 配当履歴のリスト
    """
    return (
        db.query(models.Dividend)
        .filter(models.Dividend.user_id == current_user.user_id)
        .order_by(models.Dividend.payment_date.desc())
        .all()
    )

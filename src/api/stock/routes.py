from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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


@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: AsyncSession = Depends(get_db)
):
    """
    ログイントークンを取得する
    - form_data: ユーザー名とパスワード
    - 認証成功時: アクセストークンを返却
    - 認証失敗時: 401 Unauthorized
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/users/", response_model=schemas.User)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    """
    新規ユーザーを登録する
    - user: ユーザー情報（ユーザー名、メールアドレス、パスワード）
    - 登録成功時: 作成されたユーザー情報を返却
    - ユーザー名/メールアドレス重複時: 400 Bad Request
    """
    query = select(models.User).where((models.User.username == user.username) | (models.User.email == user.email))
    result = await db.execute(query)
    db_user = result.scalar_one_or_none()

    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    hashed_password = get_password_hash(user.password)
    db_user = models.User(username=user.username, email=user.email, password_hash=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.post("/stocks/", response_model=schemas.Stock)
async def create_stock(
    stock: schemas.StockCreate,
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    新規銘柄を登録する
    - stock: 銘柄情報（シンボル、名称、市場、通貨等）
    - 登録成功時: 作成された銘柄情報を返却
    - シンボル重複時: 400 Bad Request
    """
    query = select(models.Stock).where(models.Stock.symbol == stock.symbol)
    result = await db.execute(query)
    db_stock = result.scalar_one_or_none()

    if db_stock:
        raise HTTPException(status_code=400, detail="Symbol already registered")

    db_stock = models.Stock(**stock.model_dump())
    db.add(db_stock)
    await db.commit()
    await db.refresh(db_stock)
    return db_stock


@router.get("/stocks/", response_model=List[schemas.StockWithRelations])
async def list_stocks(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    market: schemas.StockMarket | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    登録されている銘柄一覧を取得する
    - market: 市場でフィルタリング（オプション）
    - 成功時: 銘柄情報のリストを返却
    """
    query = select(models.Stock)
    if market:
        query = query.where(models.Stock.market == market)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/transactions/", response_model=schemas.Transaction)
async def create_transaction(
    transaction: schemas.TransactionCreate,
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    新規取引を登録する
    - transaction: 取引情報（銘柄、数量、価格、取引種別等）
    - 登録成功時: 作成された取引情報を返却
    - 銘柄不存在時: 404 Not Found
    - 売却時の保有数量不足: 400 Bad Request
    """
    # 株式の存在確認
    stock_query = select(models.Stock).where(models.Stock.symbol == transaction.symbol)
    stock_result = await db.execute(stock_query)
    stock = stock_result.scalar_one_or_none()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    # 取引情報の登録
    db_transaction = models.Transaction(**transaction.model_dump(), user_id=current_user.user_id)
    db.add(db_transaction)

    # 保有情報の更新
    holding_query = select(models.Holding).where(
        models.Holding.user_id == current_user.user_id, models.Holding.symbol == transaction.symbol
    )
    holding_result = await db.execute(holding_query)
    holding = holding_result.scalar_one_or_none()

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

        holding.quantity -= transaction.quantity
        if holding.quantity == 0:
            await db.delete(holding)
        else:
            holding.total_cost = holding.average_cost * holding.quantity

    await db.commit()
    return db_transaction


@router.get("/transactions/", response_model=List[schemas.Transaction])
async def list_transactions(
    current_user: Annotated[schemas.User, Depends(get_current_user)], db: AsyncSession = Depends(get_db)
):
    """
    ユーザーの取引履歴を取得する
    - 成功時: 取引情報のリストを返却（日付降順）
    """
    query = (
        select(models.Transaction)
        .where(models.Transaction.user_id == current_user.user_id)
        .order_by(models.Transaction.transaction_date.desc())
    )

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/portfolio/summary", response_model=schemas.PortfolioSummary)
async def get_portfolio_summary(
    current_user: Annotated[schemas.User, Depends(get_current_user)], db: AsyncSession = Depends(get_db)
):
    """
    ポートフォリオのサマリー情報を取得する
    - 取得情報:
        - 総コスト
        - 総時価評価額
        - 未実現損益
        - 実現損益
        - 配当総額
        - 現金残高
        - 市場別保有額
        - 通貨別保有額
    """
    # 保有銘柄の取得
    holdings_query = select(models.Holding).where(models.Holding.user_id == current_user.user_id)
    holdings_result = await db.execute(holdings_query)
    holdings = holdings_result.scalars().all()

    holdings_by_market = {}
    holdings_by_currency = {}
    total_market_value = 0
    total_cost = 0

    for holding in holdings:
        stock_query = select(models.Stock).where(models.Stock.symbol == holding.symbol)
        stock_result = await db.execute(stock_query)
        stock = stock_result.scalar_one_or_none()

        market_value = holding.market_value or 0

        holdings_by_market[stock.market] = holdings_by_market.get(stock.market, 0) + market_value
        holdings_by_currency[stock.currency] = holdings_by_currency.get(stock.currency, 0) + market_value

        total_market_value += market_value
        total_cost += holding.total_cost

    # 配当総額の集計
    dividend_query = select(func.sum(models.Dividend.total_amount)).where(models.Dividend.user_id == current_user.user_id)
    dividend_result = await db.execute(dividend_query)
    total_dividend = dividend_result.scalar() or 0

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
async def list_holdings(current_user: Annotated[schemas.User, Depends(get_current_user)], db: AsyncSession = Depends(get_db)):
    """
    ユーザーの保有銘柄一覧を取得する
    - 取得情報:
        - シンボル
        - 数量
        - 平均取得単価
        - 取得総額
        - 時価評価額
    """
    query = select(models.Holding).where(models.Holding.user_id == current_user.user_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/dividends/", response_model=schemas.Dividend)
async def create_dividend(
    dividend: schemas.DividendCreate,
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    配当情報を登録する
    - dividend: 配当情報（銘柄、配当額、配当日等）
    - 登録成功時: 作成された配当情報を返却
    - 銘柄不存在時: 404 Not Found
    """
    # 株式の存在確認
    stock_query = select(models.Stock).where(models.Stock.symbol == dividend.symbol)
    stock_result = await db.execute(stock_query)
    stock = stock_result.scalar_one_or_none()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    db_dividend = models.Dividend(**dividend.model_dump(), user_id=current_user.user_id)
    db.add(db_dividend)
    await db.commit()
    await db.refresh(db_dividend)
    return db_dividend


@router.get("/dividends/", response_model=List[schemas.Dividend])
async def list_dividends(current_user: Annotated[schemas.User, Depends(get_current_user)], db: AsyncSession = Depends(get_db)):
    """
    ユーザーの配当履歴を取得する
    - 成功時: 配当情報のリストを返却（支払日降順）
    """
    query = (
        select(models.Dividend)
        .where(models.Dividend.user_id == current_user.user_id)
        .order_by(models.Dividend.payment_date.desc())
    )

    result = await db.execute(query)
    return result.scalars().all()

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from typing import List

from .database import get_db
from .auth import (
    get_current_user,
    create_access_token,
    get_password_hash,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from .models.models import User, Stock, Transaction, Holding, Favorite
from . import schemas

app = FastAPI(title="InvestLogix API")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/token", response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.username == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/users/", response_model=schemas.UserResponse)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = User(
        username=user.username,
        email=user.email,
        password_hash=get_password_hash(user.password),
    )
    db.add(db_user)
    try:
        await db.commit()
        await db.refresh(db_user)
        return db_user
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already registered")


@app.get("/stocks/", response_model=List[schemas.StockResponse])
async def get_stocks(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Stock))
    return result.scalars().all()


@app.post("/transactions/", response_model=schemas.TransactionResponse)
async def create_transaction(
    transaction: schemas.TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 株式の存在確認
    stock_result = await db.execute(select(Stock).where(Stock.symbol == transaction.symbol))
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    # トランザクション作成
    db_transaction = Transaction(
        user_id=current_user.user_id,
        symbol=transaction.symbol,
        transaction_type=transaction.transaction_type,
        quantity=transaction.quantity,
        price=transaction.price,
    )
    db.add(db_transaction)

    # ホールディングの更新
    holding_result = await db.execute(
        select(Holding).where(
            Holding.user_id == current_user.user_id,
            Holding.symbol == transaction.symbol,
        )
    )
    holding = holding_result.scalar_one_or_none()

    if transaction.transaction_type == "buy":
        if holding:
            # 既存のホールディングを更新
            total_cost = (holding.average_cost * holding.quantity) + (transaction.price * transaction.quantity)
            total_quantity = holding.quantity + transaction.quantity
            holding.average_cost = total_cost / total_quantity
            holding.quantity = total_quantity
        else:
            # 新規ホールディングを作成
            holding = Holding(
                user_id=current_user.user_id,
                symbol=transaction.symbol,
                quantity=transaction.quantity,
                average_cost=transaction.price,
            )
            db.add(holding)
    else:  # sell
        if not holding or holding.quantity < transaction.quantity:
            raise HTTPException(status_code=400, detail="Insufficient stocks to sell")
        holding.quantity -= transaction.quantity
        if holding.quantity == 0:
            await db.delete(holding)

    try:
        await db.commit()
        await db.refresh(db_transaction)
        return db_transaction
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Transaction failed")


@app.get("/holdings/", response_model=List[schemas.HoldingResponse])
async def get_holdings(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Holding).where(Holding.user_id == current_user.user_id))
    return result.scalars().all()


@app.post("/favorites/", response_model=schemas.FavoriteResponse)
async def add_favorite(
    favorite: schemas.FavoriteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_favorite = Favorite(user_id=current_user.user_id, symbol=favorite.symbol)
    db.add(db_favorite)
    try:
        await db.commit()
        await db.refresh(db_favorite)
        return db_favorite
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Stock already in favorites")


@app.get("/favorites/", response_model=List[schemas.FavoriteResponse])
async def get_favorites(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Favorite).where(Favorite.user_id == current_user.user_id))
    return result.scalars().all()


@app.delete("/favorites/{symbol}")
async def remove_favorite(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Favorite).where(Favorite.user_id == current_user.user_id, Favorite.symbol == symbol))
    favorite = result.scalar_one_or_none()
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    await db.delete(favorite)
    await db.commit()
    return {"detail": "Favorite removed successfully"}

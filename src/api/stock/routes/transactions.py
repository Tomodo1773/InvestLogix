from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..schemas import (
    AccountType,
    CsvTransactionPreview,
    ImportConfirmRequest,
    ImportConfirmResponse,
    ImportPreviewResponse,
    MonthlySummary,
    Transaction,
    TransactionCreate,
    TransactionType,
    TransactionWithPL,
    User,
    YearlySummary,
)
from ..services.csv_import_service import detect_new_transactions, parse_csv_content
from ..services.stock_service import StockNotFoundError
from ..services.transaction_service import TransactionService

router = APIRouter()


@router.post("/", response_model=Transaction)
async def create_transaction(
    transaction: TransactionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    新規取引を登録する
    - transaction: 取引情報（銘柄、数量、価格、取引種別等）
    - 登録成功時: 作成された取引情報を返却
    - 銘柄不存在時: 404 Not Found
    - 売却時の保有数量不足: 400 Bad Request
    """
    transaction_service = TransactionService(db)
    try:
        db_transaction = await transaction_service.create_transaction(transaction, current_user.user_id)
        if not db_transaction:
            raise HTTPException(status_code=400, detail="Insufficient shares")
        return db_transaction
    except StockNotFoundError:
        raise HTTPException(status_code=404, detail="Stock not found")


@router.get("/", response_model=List[Transaction | TransactionWithPL])
async def list_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    symbol: Optional[str] = Query(None, description="シンボルでフィルタリング"),
    include_unrealized_pl: bool = Query(False, description="買付に未実現損益を含める（symbolと併用）"),
    db: AsyncSession = Depends(get_db),
):
    """
    ユーザーの取引履歴を取得する
    - 成功時: 取引情報のリストを返却（日付降順）
    - 返却データには、銘柄名(stock_name)も含まれる
    - symbolパラメータを指定すると、該当する銘柄のみをフィルタリングして返却
    - include_unrealized_pl=trueかつsymbol指定時、買付取引に未実現損益（unrealized_pl, unrealized_pl_percentage）を含める
    """
    transaction_service = TransactionService(db)
    return await transaction_service.list_transactions(current_user.user_id, symbol, include_unrealized_pl)


@router.get("/monthly-summary", response_model=List[MonthlySummary])
async def get_monthly_transaction_summary(
    current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db)
):
    """
    月ごとのトランザクション集計を取得する

    Returns:
        List[MonthlySummary]: 月ごとの口座種別別購入金額集計
    """
    transaction_service = TransactionService(db)
    return await transaction_service.get_monthly_summary(current_user.user_id)


@router.get("/yearly-summary", response_model=List[YearlySummary])
async def get_yearly_transaction_summary(
    current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db)
):
    """
    年ごとのトランザクション集計を取得する

    Returns:
        List[YearlySummary]: 年ごとの口座種別別購入金額集計
    """
    transaction_service = TransactionService(db)
    return await transaction_service.get_yearly_summary(current_user.user_id)


@router.post("/import/preview", response_model=ImportPreviewResponse)
async def preview_csv_import(
    file: UploadFile,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    CSVをアップロードして差分プレビューを取得

    Args:
        file: SBI証券からエクスポートした取引履歴CSV
        current_user: 認証済みユーザー
        db: データベースセッション

    Returns:
        ImportPreviewResponse: 新規取引のプレビューと統計情報
    """
    # ファイルサイズチェック（1MB制限）
    MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        logger.error(
            "CSVファイルサイズ超過 action=csv_preview user_id={} size={} max_size={}",
            current_user.user_id,
            len(content),
            MAX_FILE_SIZE,
        )
        raise HTTPException(status_code=400, detail="ファイルサイズが1MBを超えています")

    # CSVパース
    try:
        parsed_transactions, parse_errors = parse_csv_content(content)
        logger.info(
            "CSVをパースしました action=csv_preview user_id={} parsed_count={} error_count={}",
            current_user.user_id,
            len(parsed_transactions),
            len(parse_errors),
        )
    except ValueError as e:
        logger.error("CSVパースエラー action=csv_preview user_id={} error={}", current_user.user_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))

    # 既存取引を取得
    transaction_service = TransactionService(db)
    existing_transactions = await transaction_service.list_transactions(current_user.user_id)

    # 差分検出
    new_transactions = detect_new_transactions(parsed_transactions, existing_transactions)
    logger.info(
        "CSV差分を検出しました action=csv_preview user_id={} new_count={} existing_count={} csv_total_count={}",
        current_user.user_id,
        len(new_transactions),
        len(existing_transactions),
        len(parsed_transactions),
    )

    # CsvTransactionPreviewに変換
    preview_list = [
        CsvTransactionPreview(
            symbol=tx.symbol,
            name=tx.name,
            transaction_type=TransactionType.BUY if tx.transaction_type == "買付" else TransactionType.SELL,
            quantity=tx.quantity,
            price=tx.price,
            usd_price=tx.usd_price,
            account_type=AccountType(tx.account_type),
            fee=tx.fee,
            tax=tx.tax,
            transaction_date=tx.transaction_date,
        )
        for tx in new_transactions
    ]

    return ImportPreviewResponse(
        new_transactions=preview_list,
        existing_count=len(existing_transactions),
        csv_total_count=len(parsed_transactions),
        skipped_count=len(parse_errors),
        errors=parse_errors,
    )


@router.post("/import/confirm", response_model=ImportConfirmResponse)
async def confirm_csv_import(
    request: ImportConfirmRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    プレビューで確認した取引を一括登録

    Args:
        request: 登録する取引のリスト
        current_user: 認証済みユーザー
        db: データベースセッション

    Returns:
        ImportConfirmResponse: 登録結果
    """
    transaction_service = TransactionService(db)
    created_count = 0
    failed_count = 0
    errors = []

    logger.info(
        "CSV取引一括登録を開始します action=csv_confirm user_id={} target_count={}",
        current_user.user_id,
        len(request.transactions),
    )

    for transaction in request.transactions:
        try:
            created_transaction = await transaction_service.create_transaction(
                transaction, current_user.user_id
            )
            if created_transaction is None:
                failed_count += 1
                errors.append(
                    f"登録失敗: {transaction.symbol} - 保有なしの売却/数量不足などの理由で登録できませんでした"
                )
                logger.error(
                    "CSV取引登録失敗 action=csv_confirm user_id={} symbol={} error=invalid_transaction_condition",
                    current_user.user_id,
                    transaction.symbol,
                )
            else:
                created_count += 1
        except StockNotFoundError:
            failed_count += 1
            errors.append(f"銘柄が見つかりません: {transaction.symbol}")
            logger.error(
                "CSV取引登録失敗 action=csv_confirm user_id={} symbol={} error=stock_not_found",
                current_user.user_id,
                transaction.symbol,
            )
        except Exception as e:
            failed_count += 1
            errors.append(f"登録失敗: {transaction.symbol} - {str(e)}")
            logger.error(
                "CSV取引登録失敗 action=csv_confirm user_id={} symbol={} error={}",
                current_user.user_id,
                transaction.symbol,
                str(e),
            )

    logger.info(
        "CSV取引一括登録が完了しました action=csv_confirm user_id={} created_count={} failed_count={}",
        current_user.user_id,
        created_count,
        failed_count,
    )

    return ImportConfirmResponse(created_count=created_count, failed_count=failed_count, errors=errors)

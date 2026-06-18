from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user, get_db_for_user
from ..schemas import (
    CsvDividendPreview,
    Dividend,
    DividendBySymbol,
    DividendCreate,
    DividendImportConfirmRequest,
    DividendImportConfirmResponse,
    DividendImportPreviewResponse,
    MonthlyDividend,
    User,
)
from ..services.dividend_csv_import_service import detect_new_dividends, parse_dividend_csv_content
from ..services.dividend_service import DividendService
from ..services.stock_service import StockNotFoundError

router = APIRouter()


@router.post("/", response_model=Dividend)
async def create_dividend(
    dividend: DividendCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db_for_user),
):
    """
    配当情報を登録する
    - dividend: 配当情報（銘柄、配当額、配当日等）
    - 登録成功時: 作成された配当情報を返却
    - 銘柄不存在時: 404 Not Found
    """
    dividend_service = DividendService(db)
    try:
        db_dividend = await dividend_service.create_dividend(dividend, current_user.user_id)
        return db_dividend
    except StockNotFoundError:
        raise HTTPException(status_code=404, detail="Stock not found")


@router.get("/", response_model=List[Dividend])
async def list_dividends(
    current_user: Annotated[User, Depends(get_current_user)],
    symbol: Optional[str] = Query(None, description="シンボルでフィルタリング"),
    db: AsyncSession = Depends(get_db_for_user),
):
    """
    ユーザーの配当履歴を取得する
    - 成功時: 配当情報のリストを返却（支払日降順）
    - symbolパラメータを指定すると、該当する銘柄のみをフィルタリングして返却
    """
    dividend_service = DividendService(db)
    return await dividend_service.list_dividends(current_user.user_id, symbol)


@router.get("/monthly", response_model=List[MonthlyDividend])
async def get_monthly_dividends(
    current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db_for_user)
):
    """
    月次の配当金集計を取得する
    - 成功時: 月ごとの配当金集計のリスト（年月と配当金額）を返却
    """
    dividend_service = DividendService(db)
    return await dividend_service.get_monthly_dividends(current_user.user_id)


@router.get("/by-symbol", response_model=List[DividendBySymbol])
async def get_dividends_by_symbol(
    current_user: Annotated[User, Depends(get_current_user)], db: AsyncSession = Depends(get_db_for_user)
):
    """
    銘柄別の配当金集計を取得する
    - 成功時: 銘柄ごとの配当金集計のリスト（銘柄コード・銘柄名・配当金額）を金額降順で返却
    """
    dividend_service = DividendService(db)
    return await dividend_service.get_dividends_by_symbol(current_user.user_id)


@router.post("/import/preview", response_model=DividendImportPreviewResponse)
async def preview_dividend_csv_import(
    file: UploadFile,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db_for_user),
):
    """
    配当金CSVをアップロードして差分プレビューを取得

    Args:
        file: SBI証券からエクスポートした配当金・分配金CSV
        current_user: 認証済みユーザー
        db: データベースセッション

    Returns:
        DividendImportPreviewResponse: 新規配当金のプレビューと統計情報
    """
    # ファイルサイズチェック（1MB制限）
    MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        logger.error(
            "配当金CSVファイルサイズ超過 action=dividend_csv_preview user_id={} size={} max_size={}",
            current_user.user_id,
            len(content),
            MAX_FILE_SIZE,
        )
        raise HTTPException(status_code=400, detail="ファイルサイズが1MBを超えています")

    # CSVパース
    try:
        parsed_dividends, parse_errors = parse_dividend_csv_content(content)
        logger.info(
            "配当金CSVをパースしました action=dividend_csv_preview user_id={} parsed_count={} error_count={}",
            current_user.user_id,
            len(parsed_dividends),
            len(parse_errors),
        )
    except ValueError as e:
        logger.error(
            "配当金CSVパースエラー action=dividend_csv_preview user_id={} error={}",
            current_user.user_id,
            str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))

    # 既存配当金を取得
    dividend_service = DividendService(db)
    existing_dividends = await dividend_service.list_dividends(current_user.user_id)

    # 差分検出
    new_dividends = detect_new_dividends(parsed_dividends, existing_dividends)
    logger.info(
        "配当金CSV差分を検出しました action=dividend_csv_preview user_id={} new_count={} existing_count={} csv_total_count={}",
        current_user.user_id,
        len(new_dividends),
        len(existing_dividends),
        len(parsed_dividends),
    )

    # CsvDividendPreviewに変換
    preview_list = [
        CsvDividendPreview(
            symbol=div.symbol,
            name=div.name,
            payment_date=div.payment_date,
            shares_owned=div.shares_owned,
            total_amount=div.total_amount,
        )
        for div in new_dividends
    ]

    return DividendImportPreviewResponse(
        new_dividends=preview_list,
        existing_count=len(existing_dividends),
        csv_total_count=len(parsed_dividends),
        skipped_count=len(parse_errors),
        errors=parse_errors,
    )


@router.post("/import/confirm", response_model=DividendImportConfirmResponse)
async def confirm_dividend_csv_import(
    request: DividendImportConfirmRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db_for_user),
):
    """
    プレビューで確認した配当金を一括登録

    Args:
        request: 登録する配当金のリスト
        current_user: 認証済みユーザー
        db: データベースセッション

    Returns:
        DividendImportConfirmResponse: 登録結果
    """
    dividend_service = DividendService(db)
    created_count = 0
    failed_count = 0
    errors = []

    logger.info(
        "配当金CSV一括登録を開始します action=dividend_csv_confirm user_id={} target_count={}",
        current_user.user_id,
        len(request.dividends),
    )

    for dividend in request.dividends:
        try:
            await dividend_service.create_dividend(dividend, current_user.user_id)
            created_count += 1
        except StockNotFoundError:
            failed_count += 1
            errors.append(f"銘柄が見つかりません: {dividend.symbol}")
            logger.error(
                "配当金CSV登録失敗 action=dividend_csv_confirm user_id={} symbol={} error=stock_not_found",
                current_user.user_id,
                dividend.symbol,
            )
        except Exception as e:
            failed_count += 1
            errors.append(f"登録失敗: {dividend.symbol} - {str(e)}")
            logger.error(
                "配当金CSV登録失敗 action=dividend_csv_confirm user_id={} symbol={} error={}",
                current_user.user_id,
                dividend.symbol,
                str(e),
            )

    logger.info(
        "配当金CSV一括登録が完了しました action=dividend_csv_confirm user_id={} created_count={} failed_count={}",
        current_user.user_id,
        created_count,
        failed_count,
    )

    return DividendImportConfirmResponse(
        created_count=created_count, failed_count=failed_count, errors=errors
    )

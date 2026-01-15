"""
ログ設定モジュール
loguruを使用したアプリケーション全体のログ設定
"""

import sys
from pathlib import Path

from loguru import logger

from .database import settings


def configure_logging():
    """
    アプリケーション全体のログ設定を行う

    - 標準出力への出力(常時)
    - ファイル出力(ローカル開発時のみ、1日ローテーション、7日保持)
    - ログレベルは環境変数 LOG_LEVEL で制御(デフォルト: INFO)
    """
    # デフォルトのハンドラーを削除
    logger.remove()

    # 標準出力への出力設定
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL.value.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )

    # ローカル開発時のみファイル出力を有効化
    if settings.HOST == "0.0.0.0" and settings.PORT == 8000:
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)

        logger.add(
            log_dir / "investlogix_{time:YYYY-MM-DD}.log",
            level=settings.LOG_LEVEL.value.upper(),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="00:00",  # 毎日0時にローテーション
            retention="7 days",  # 7日間保持
            compression="zip",  # 圧縮して保存
            encoding="utf-8",
        )

    logger.info("Logging configured successfully")
    return logger

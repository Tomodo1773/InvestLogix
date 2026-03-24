from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel

from ..database import settings
from ..utils.cache import timed_cache

SYSTEM_PROMPT = (
    "投資信託のファンド名から、主要な投資対象の通貨エクスポージャーを判定してください。"
    "ISO 4217の3文字通貨コードで回答してください。"
    "複数通貨に分散している場合は、最も比率の高い通貨を選んでください。"
    "全世界株式など特定通貨に偏らない場合はUSDとしてください。"
)

_openai_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


class CurrencyClassification(BaseModel):
    """AI分類の構造化出力スキーマ"""

    currency: str


@timed_cache(seconds=86400)
async def classify_fund_currency(fund_name: str) -> str:
    """投資信託のファンド名から通貨エクスポージャーを分類する。

    Args:
        fund_name: ファンド名（例: "eMAXIS Slim 米国株式(S&P500)"）

    Returns:
        ISO 4217 通貨コード（例: "USD", "JPY", "EUR"）。
        API未設定・エラー時は "JPY" を返す。
    """
    if not settings.OPENAI_API_KEY:
        logger.warning(
            "OPENAI_API_KEYが未設定のため通貨分類をスキップします action=external_io fund_name={}", fund_name
        )
        return "JPY"

    try:
        client = get_openai_client()
        response = await client.responses.parse(
            model="gpt-5.4-mini",
            instructions=SYSTEM_PROMPT,
            input=fund_name,
            text_format=CurrencyClassification,
        )
        result = response.output_parsed
        logger.info("通貨分類完了 action=external_io fund_name={} currency={}", fund_name, result.currency)
        return result.currency
    except Exception:
        logger.exception("通貨分類失敗、JPYにフォールバック action=external_io fund_name={}", fund_name)
        return "JPY"

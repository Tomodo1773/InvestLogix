"""週次騰落率ランキングの「変動理由」を OpenAI gpt-5.4 + web 検索で生成する。

LINE 週次騰落率通知の Flex Message に続けて送るテキスト本文を生成するサービス。
"""

from loguru import logger

from ..database import settings
from ..schemas import StockWeeklyPerformance
from .classification_service import get_openai_client

OPENAI_MODEL: str = "gpt-5.4"
REASONING_EFFORT: str = "high"
MAX_OUTPUT_CHARS: int = 1000
REQUEST_TIMEOUT_SEC: float = 180.0

CHANGE_REASON_SYSTEM_PROMPT: str = (
    "あなたは日本の個人投資家向けの株式市況アナリストです。"
    "入力された「週間騰落率ランキング」（上位5銘柄・下位5銘柄、最大10銘柄、日本株と米国株が混在）について、"
    "直近1週間の値動きの主因をweb検索で調査し、日本語でまとめてください。\n\n"
    "必須の遵守事項:\n"
    "- 全体で1000文字以内（厳守）。超えそうなら銘柄を統合して要約すること。\n"
    "- 同じセクターで連れ高・連れ安した銘柄、個別材料が乏しい銘柄はまとめて1行で記述してよい。"
    "例: 「AAAA・BBBBは半導体セクターの連れ高」\n"
    "- 個別に明確な材料（決算・ガイダンス・M&A・アナリスト格上げ/格下げ・規制・ショック等）がある銘柄は"
    "銘柄ごとに1〜2文で説明。\n"
    "- 銘柄の識別は「銘柄名」のみ。銘柄コード（ティッカー/証券コード）は冗長なので出力に含めない。\n"
    "- 絵文字・記号による装飾は使わない。文字数節約のためプレーンな日本語テキストのみ。\n"
    "- 出典URLや引用マーク、脚注は出力に含めない。\n"
    "- web検索で確実な情報が見つからない銘柄は推測せず"
    "「特段の材料は確認できず（地合いの影響と思われる）」と簡潔に記載する。\n"
    "- 冗長な前置き・まとめの挨拶・免責事項は入れない。本文のみ。\n"
    "- 構成: 最初に「上昇トップ」セクション、次に「下落ワースト」セクション。"
    "各セクションは銘柄（またはまとめたグループ）ごとに改行。"
)


def _format_performers_for_prompt(
    top_performers: list[StockWeeklyPerformance],
    bottom_performers: list[StockWeeklyPerformance],
) -> str:
    """OpenAI への入力として、上位・下位銘柄のリストを文字列化する。"""

    def _format_line(rank: int, p: StockWeeklyPerformance) -> str:
        sign = "+" if p.change_rate >= 0 else ""
        return f"{rank}. {p.name}（{p.symbol}）: {sign}{p.change_rate:.2f}%"

    top_block = "\n".join(_format_line(i + 1, p) for i, p in enumerate(top_performers))
    bottom_block = "\n".join(_format_line(i + 1, p) for i, p in enumerate(bottom_performers))

    return (
        "対象期間: 直近1週間（およそ過去5営業日）\n\n"
        f"【上昇トップ】\n{top_block}\n\n"
        f"【下落ワースト】\n{bottom_block}\n\n"
        "これらの銘柄について、直近1週間の値動きの主因をweb検索で調査し、"
        "システム指示に従って1000文字以内でまとめてください。"
    )


def _trim_to_max_chars(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    """指定文字数を超えたら句点または改行で切り詰め、末尾に「…」を付加する。"""
    if len(text) <= max_chars:
        return text

    truncated = text[: max_chars - 1]
    for sep in ("。", "\n"):
        idx = truncated.rfind(sep)
        if idx > max_chars // 2:
            return truncated[: idx + 1] + "…"

    return truncated + "…"


async def generate_change_reasons(
    top_performers: list[StockWeeklyPerformance],
    bottom_performers: list[StockWeeklyPerformance],
) -> str | None:
    """騰落銘柄リストから変動理由テキストを生成する。

    Args:
        top_performers: 上昇トップ銘柄のリスト
        bottom_performers: 下落ワースト銘柄のリスト

    Returns:
        1000文字以内の日本語テキスト。API未設定・失敗・空レスポンス時は None。
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEYが未設定のため変動理由生成をスキップします action=external_io")
        return None

    if not top_performers and not bottom_performers:
        logger.info("対象銘柄が空のため変動理由生成をスキップします action=external_io")
        return None

    user_input = _format_performers_for_prompt(top_performers, bottom_performers)

    try:
        client = get_openai_client()
        logger.info(
            "OpenAIに変動理由生成リクエストを送信します action=external_io model={} top={} bottom={}",
            OPENAI_MODEL,
            len(top_performers),
            len(bottom_performers),
        )
        response = await client.responses.create(
            model=OPENAI_MODEL,
            instructions=CHANGE_REASON_SYSTEM_PROMPT,
            input=user_input,
            reasoning={"effort": REASONING_EFFORT},
            tools=[{"type": "web_search"}],
            timeout=REQUEST_TIMEOUT_SEC,
        )
        text = response.output_text
        if not text:
            logger.warning("OpenAIレスポンスの本文が空でした action=external_io")
            return None
        trimmed = _trim_to_max_chars(text)
        logger.info("変動理由生成完了 action=external_io length={}", len(trimmed))
        return trimmed
    except Exception:
        logger.exception("変動理由生成失敗 action=external_io")
        return None

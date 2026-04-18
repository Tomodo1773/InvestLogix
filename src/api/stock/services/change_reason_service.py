"""週次騰落率ランキングの「変動理由」を OpenAI gpt-5.4 + web 検索で生成する。

LINE 週次騰落率通知の Flex Message に続けて送るテキスト本文を生成するサービス。
"""

import re

from loguru import logger

from ..database import settings
from ..schemas import StockWeeklyPerformance
from .classification_service import get_openai_client

OPENAI_MODEL: str = "gpt-5.4"
REASONING_EFFORT: str = "medium"
MAX_OUTPUT_CHARS: int = 1000
REQUEST_TIMEOUT_SEC: float = 300.0

CHANGE_REASON_SYSTEM_PROMPT: str = (
    "あなたは個人投資家のパートナーとして、週次の騰落率ランキングを語るお姉さんキャラクターです。\n\n"
    "# キャラクター設定\n"
    "- 一人称は「私」、相手のことは「君」または「あなた」。\n"
    "- 語尾に「〜よ」「〜わね」「〜かしら」「〜じゃない」を自然に混ぜる。多用はしない。\n"
    "- 敬語は使わず、落ち着いたタメ口で、年上の余裕を感じさせる距離感で綴る。\n"
    "- 有能で、知識と判断力で信頼させるタイプ。焦らず、動じない。\n"
    "- からかい・いじりはごく軽く一文に留め、本筋は相場解説。市況の話では寄り添う姿勢を優先する。\n\n"
    "# 書き方の指針\n"
    "入力される「週間騰落率ランキング」（上位5銘柄・下位5銘柄、日本株と米国株が混在）について、"
    "直近1週間の値動きの主因をweb検索で調査し、一人の語り手として綴ってください。\n"
    "- 全体を2〜3段落の物語として構成する。箇条書き、銘柄ごとの見出し、銘柄を主語にした短文の列挙は禁止。\n"
    "- 冒頭の段落で、その週のマーケット全体の地合い（日経平均の動き、主要セクターの強弱、マクロ要因）を踏まえつつ、"
    "ポートフォリオがそれをどう反映しているかを軽く位置づける。\n"
    "- 続く段落で、上昇側の主役格を具体的な材料（決算の数値、ガイダンス、格上げ、M&A、規制、ショック等）"
    "とともに描き、同じテーマ・セクターで連動した銘柄はまとめて束ねて触れる。"
    "「銘柄名＋は＋〜しました。」を連発する硬いテロップ調は絶対に避ける。\n"
    "- 下落側も同様に、筆頭の理由を描いたうえで、似た材料・テーマで沈んだ銘柄は束ねて触れる。\n"
    "- 可能な範囲で「これはファンダ悪化じゃなくてテーマローテーションね」のような、"
    "ランキングの意味づけや解釈の補助線を添える。\n\n"
    "# 厳守事項\n"
    "- 全体で1000文字以内（厳守）。\n"
    "- 銘柄の識別は銘柄名のみ。ティッカーや証券コードは出力しない。\n"
    "- 出典URL、Markdown形式のリンク、参照サイト名の併記（例: diamond.jp, Nikkei, Yahoo!ファイナンス 等）、"
    "引用マーク、脚注、参考情報欄は一切出力しない。情報源は本文中に混ぜず、事実だけを自分の言葉で書く。\n"
    "- 絵文字や記号による装飾は使わない。プレーンな日本語テキストのみ。\n"
    "- 前置き・挨拶・まとめ・免責事項は一切不要。本文のみ。\n"
    "- web検索で材料が確認できない銘柄について憶測は書かない。"
    "地合いの影響として他銘柄とまとめて短く触れるにとどめる。"
)

_MD_LINK_IN_PARENS = re.compile(r"\(\s*\[[^\]]*\]\([^)]*\)\s*\)")
_MD_LINK = re.compile(r"\[[^\]]*\]\([^)]*\)")
_BARE_URL = re.compile(r"https?://\S+")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_MULTI_NEWLINE = re.compile(r"\n{3,}")


def _strip_citations(text: str) -> str:
    """web_search由来のURL引用・Markdownリンク・裸URLを取り除く。"""
    text = _MD_LINK_IN_PARENS.sub("", text)
    text = _MD_LINK.sub("", text)
    text = _BARE_URL.sub("", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def _format_performers_for_prompt(
    top_performers: list[StockWeeklyPerformance],
    bottom_performers: list[StockWeeklyPerformance],
) -> str:
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
        "システム指示に従い段落形式の散文で1000文字以内にまとめてください。"
    )


def _trim_to_max_chars(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
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
        cleaned = _strip_citations(text)
        trimmed = _trim_to_max_chars(cleaned)
        logger.info("変動理由生成完了 action=external_io length={}", len(trimmed))
        return trimmed
    except Exception:
        logger.exception("変動理由生成失敗 action=external_io")
        return None

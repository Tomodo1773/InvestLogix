"""MCPへ公開する、厳選した参照系ツール。"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations

from .. import models
from ..schemas import AccountType
from ..services.holding_service import list_holdings as list_holdings_service
from ..utils.datetime import to_jst
from .middleware import get_user_context_from_mcp

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)

HoldingSortField = Literal[
    "market_value",
    "unrealized_pl",
    "unrealized_pl_percentage",
    "total_pl",
    "total_pl_percentage",
]
SortOrder = Literal["asc", "desc"]


class HoldingListItem(BaseModel):
    """保有銘柄の一覧・比較に必要な値。"""

    symbol: str
    stock_name: str
    market_value: float | None
    unrealized_pl: float | None
    unrealized_pl_percentage: float | None
    total_pl: float | None
    total_pl_percentage: float | None
    model_config = ConfigDict(from_attributes=True)


class ListHoldingsOutput(BaseModel):
    """保有銘柄一覧の出力。"""

    holdings: list[HoldingListItem]


class AccountHoldingOutput(BaseModel):
    """口座区分ごとの保有数量。"""

    account_type: AccountType
    quantity: float
    model_config = ConfigDict(from_attributes=True)


class HoldingDetailOutput(BaseModel):
    """指定した保有銘柄の詳細。"""

    symbol: str
    stock_name: str
    security_type: str
    currency: str
    country: str
    sector_name: str | None
    quantity: float
    average_cost: float
    total_cost: float
    current_price: float | None
    current_price_usd: float | None
    market_value: float | None
    market_value_usd: float | None
    unrealized_pl: float | None
    unrealized_pl_percentage: float | None
    realized_pl: float | None
    total_dividend: float | None
    total_pl: float | None
    total_pl_percentage: float | None
    account_holdings: list[AccountHoldingOutput]
    note: str | None
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("last_updated")
    def serialize_last_updated(self, value: datetime) -> str:
        return to_jst(value).isoformat()


def _sort_holdings(
    holdings: list[models.Holding], sort_by: HoldingSortField, order: SortOrder
) -> list[models.Holding]:
    """値がない銘柄を末尾に置き、同値はsymbol昇順で安定ソートする。"""
    holdings_by_symbol = sorted(holdings, key=lambda holding: holding.symbol)
    with_value = [holding for holding in holdings_by_symbol if getattr(holding, sort_by) is not None]
    without_value = [holding for holding in holdings_by_symbol if getattr(holding, sort_by) is None]
    with_value.sort(key=lambda holding: getattr(holding, sort_by), reverse=order == "desc")
    return [*with_value, *without_value]


def register_tools(server: MCPServer) -> None:
    """MCPツールをサーバーへ登録する。"""

    @server.tool(annotations=READ_ONLY)
    async def list_holdings(
        ctx: Context,
        sort_by: Annotated[
            HoldingSortField,
            Field(description="一覧を並べる評価額または損益指標"),
        ] = "market_value",
        order: Annotated[
            SortOrder,
            Field(description="並び順。ascは昇順、descは降順"),
        ] = "desc",
    ) -> ListHoldingsOutput:
        """現在保有中の全銘柄を、評価額または損益で並べて取得する。"""
        user_context = get_user_context_from_mcp(ctx)
        holdings = await list_holdings_service(
            user_context.db,
            user_context.user_id,
            active_only=True,
        )
        sorted_holdings = _sort_holdings(list(holdings), sort_by, order)
        return ListHoldingsOutput(
            holdings=[HoldingListItem.model_validate(holding) for holding in sorted_holdings]
        )

    @server.tool(annotations=READ_ONLY)
    async def get_holding(
        ctx: Context,
        symbol: Annotated[str, Field(min_length=1, description="銘柄コードまたはティッカーシンボル")],
    ) -> HoldingDetailOutput:
        """現在保有中の指定した1銘柄について、評価額、損益、口座内訳などの詳細を取得する。"""
        user_context = get_user_context_from_mcp(ctx)
        normalized_symbol = symbol.strip().upper()
        holdings = await list_holdings_service(
            user_context.db,
            user_context.user_id,
            symbol=normalized_symbol,
            active_only=True,
        )
        if not holdings:
            raise ValueError(f"現在保有している銘柄が見つかりません: {normalized_symbol}")
        return HoldingDetailOutput.model_validate(holdings[0])

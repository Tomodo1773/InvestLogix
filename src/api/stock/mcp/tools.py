"""MCPへ公開する、厳選した参照系ツール。"""

from datetime import datetime

from pydantic import ConfigDict, field_serializer

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations

from .. import schemas
from ..services.dividend_service import DividendService
from ..services.holding_service import list_holdings as list_holdings_service
from ..services.portfolio_service import PortfolioService
from ..utils.datetime import to_jst
from .middleware import get_user_context_from_mcp

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)


class HoldingView(schemas.HoldingBase):
    """MCP向け保有銘柄。内部のuser_idは公開しない。"""

    last_updated: datetime
    stock_name: str | None = None
    security_type: str | None = None
    currency: str | None = None
    country: str | None = None
    sector_name: str | None = None
    account_holdings: list[schemas.AccountHolding]
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("last_updated")
    def serialize_last_updated(self, value: datetime) -> str:
        return to_jst(value).isoformat()


def register_tools(server: MCPServer) -> None:
    """MCPツールをサーバーへ登録する。"""

    @server.tool(annotations=READ_ONLY)
    async def get_portfolio_summary(ctx: Context) -> schemas.PortfolioSummary:
        """現在のポートフォリオ全体の評価額、損益、配当、構成比を取得する。"""
        user_context = get_user_context_from_mcp(ctx)
        return await PortfolioService(user_context.db).get_portfolio_summary(user_context.user_id)

    @server.tool(annotations=READ_ONLY)
    async def list_holdings(ctx: Context, symbol: str | None = None) -> list[HoldingView]:
        """保有銘柄を一覧する。symbolを指定すると1銘柄に絞り込む。"""
        user_context = get_user_context_from_mcp(ctx)
        holdings = await list_holdings_service(user_context.db, user_context.user_id, symbol=symbol)
        return [HoldingView.model_validate(holding) for holding in holdings]

    @server.tool(annotations=READ_ONLY)
    async def get_monthly_dividends(ctx: Context) -> list[schemas.MonthlyDividend]:
        """税・手数料控除後の月次配当額を時系列で取得する。"""
        user_context = get_user_context_from_mcp(ctx)
        rows = await DividendService(user_context.db).get_monthly_dividends(user_context.user_id)
        return [schemas.MonthlyDividend.model_validate(row) for row in rows]

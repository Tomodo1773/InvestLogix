"""Streamable HTTPで提供するInvestLogix MCPアプリケーション。"""

from mcp.server import MCPServer

from ..database import settings
from .middleware import AccessUserContextMiddleware
from .tools import register_tools

mcp = MCPServer(
    name="investlogix",
    title="InvestLogix",
    description="認証した利用者自身の投資ポートフォリオを参照するMCPサーバー",
    instructions="参照系ツールだけを提供します。金額は特記がなければ日本円です。",
    version="2.0.0",
)
register_tools(mcp)

mcp_http_app = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
    host=settings.HOST,
)

# 認証をSDKの各ツールではなくASGI境界で強制する。initialize/tools/listを含め、
# Cloud Runへ直接届いた未認証リクエストがMCP層へ入ることはない。
app = AccessUserContextMiddleware(mcp_http_app)

"""Cloudflare Access認証をMCPのASGIアプリ全体へ強制するミドルウェア。"""

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from typing import cast

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from mcp.server.mcpserver import Context

from ..cloudflare_access import (
    ACCESS_JWT_HEADER,
    AccessIdentity,
    AccessTokenError,
    authenticate_access_request,
)
from ..database import session_scope
from ..user_context import UserContext, UserNotRegisteredError, create_user_context

USER_CONTEXT_SCOPE_KEY = "investlogix.user_context"
IdentityProvider = Callable[[str | None], Awaitable[AccessIdentity]]
SessionScopeFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class AccessUserContextMiddleware:
    """Access JWT検証・User解決・RLS設定を済ませてからMCPへ渡す。"""

    def __init__(
        self,
        app: ASGIApp,
        identity_provider: IdentityProvider = authenticate_access_request,
        session_scope_factory: SessionScopeFactory = session_scope,
    ):
        self.app = app
        self.identity_provider = identity_provider
        self.session_scope_factory = session_scope_factory

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        token = Headers(scope=scope).get(ACCESS_JWT_HEADER)
        try:
            identity = await self.identity_provider(token)
        except AccessTokenError as error:
            logger.warning("MCP Access JWTの検証に失敗しました action=verify reason={}", str(error))
            await self._error_response(401, "認証が必要です", scope, receive, send)
            return

        async with self.session_scope_factory() as db:
            try:
                user_context = await create_user_context(db, identity)
            except UserNotRegisteredError:
                logger.warning("MCP Access IDに対応するUserがいません action=select email={}", identity.email)
                await self._error_response(
                    403,
                    "このアカウントはInvestLogixに登録されていません",
                    scope,
                    receive,
                    send,
                )
                return

            scope[USER_CONTEXT_SCOPE_KEY] = user_context
            await self.app(scope, receive, send)

    @staticmethod
    async def _error_response(
        status_code: int,
        detail: str,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        await JSONResponse({"detail": detail}, status_code=status_code)(scope, receive, send)


def get_user_context_from_mcp(context: Context) -> UserContext:
    """SDKのリクエストコンテキストから認証済みユーザーコンテキストを得る。"""
    request = context.request_context.request
    if request is None:
        raise RuntimeError("HTTPリクエストコンテキストがありません")

    user_context = request.scope.get(USER_CONTEXT_SCOPE_KEY)
    if user_context is None:
        raise RuntimeError("認証済みユーザーコンテキストがありません")
    return cast(UserContext, user_context)

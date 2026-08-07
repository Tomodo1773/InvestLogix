from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2
import pytest
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker

from stock.app import app as api_app
from stock.auth import get_access_identity
from stock.cloudflare_access import AccessIdentity, AccessTokenError
from stock.mcp.app import mcp_http_app
from stock.mcp.middleware import AccessUserContextMiddleware
from stock.schemas import UserBase
from stock.services.user_service import UserService
from tests.conftest import TEST_ACCESS_ISSUER


async def _create_user(engine: AsyncEngine, username: str, email: str) -> AccessIdentity:
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        user = await UserService(session).create_user(UserBase(username=username, email=email))
        identity = AccessIdentity(
            issuer=TEST_ACCESS_ISSUER,
            subject=f"access-{user.user_id}",
            email=email,
        )
        user.access_issuer = identity.issuer
        user.access_subject = identity.subject
        await session.commit()
    return identity


def _session_scope_factory(engine: AsyncEngine):
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def test_session_scope() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return test_session_scope


def _mcp_app(engine: AsyncEngine, identity: AccessIdentity) -> AccessUserContextMiddleware:
    async def provide_identity(token: str | None) -> AccessIdentity:
        if token != "test-token":
            raise AccessTokenError("テスト用Access JWTがありません")
        return identity

    return AccessUserContextMiddleware(
        mcp_http_app,
        identity_provider=provide_identity,
        session_scope_factory=_session_scope_factory(engine),
    )


@pytest.mark.asyncio
async def test_mcp_rejects_request_without_access_jwt(setup_database: AsyncEngine):
    identity = await _create_user(setup_database, "mcp-user", "mcp@example.com")
    transport = httpx2.ASGITransport(app=_mcp_app(setup_database, identity))

    async with httpx2.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/mcp", json={})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_mcp_rejects_unregistered_access_user(setup_database: AsyncEngine):
    identity = AccessIdentity(
        issuer=TEST_ACCESS_ISSUER,
        subject="unknown-subject",
        email="unknown@example.com",
    )
    transport = httpx2.ASGITransport(app=_mcp_app(setup_database, identity))

    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Cf-Access-Jwt-Assertion": "test-token"},
    ) as client:
        response = await client.post("/mcp", json={})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_mcp_lists_read_only_tools_and_keeps_user_data_separate(
    client,
    auth_user: AccessIdentity,
    create_transaction,
    create_dividend,
    setup_database: AsyncEngine,
):
    await create_transaction(
        {
            "symbol": "8058",
            "transaction_type": "buy",
            "quantity": 100,
            "price": 3000,
            "account_type": "NISA(成長投資枠)",
            "fee": 0,
            "tax": 0,
            "transaction_date": "2024-01-01T00:00:00+09:00",
        }
    )
    await create_dividend(
        {
            "symbol": "8058",
            "payment_date": "2024-03-01T00:00:00+09:00",
            "shares_owned": 100,
            "total_amount": 2000,
            "tax": 400,
            "fee": 100,
        }
    )

    other_identity = await _create_user(setup_database, "other-user", "other@example.com")
    api_app.dependency_overrides[get_access_identity] = lambda: other_identity
    response = await client.post(
        "/api/v1/transactions/",
        json={
            "symbol": "AAPL",
            "transaction_type": "buy",
            "quantity": 10,
            "price": 36000,
            "usd_price": 240,
            "account_type": "NISA(成長投資枠)",
            "fee": 0,
            "tax": 0,
            "transaction_date": "2024-01-01T00:00:00+09:00",
        },
    )
    assert response.status_code == 200

    mcp_app = _mcp_app(setup_database, auth_user)
    transport = httpx2.ASGITransport(app=mcp_app)
    async with (
        mcp_http_app.router.lifespan_context(mcp_http_app),
        httpx2.AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Cf-Access-Jwt-Assertion": "test-token"},
        ) as http_client,
        Client(streamable_http_client("http://test/mcp", http_client=http_client)) as mcp_client,
    ):
        tools = await mcp_client.list_tools()
        holdings_result = await mcp_client.call_tool("list_holdings")
        summary_result = await mcp_client.call_tool("get_portfolio_summary")
        dividends_result = await mcp_client.call_tool("get_monthly_dividends")

    assert {tool.name for tool in tools.tools} == {
        "get_portfolio_summary",
        "list_holdings",
        "get_monthly_dividends",
    }
    assert all(tool.annotations and tool.annotations.read_only_hint for tool in tools.tools)
    holdings = holdings_result.structured_content["result"]
    assert [holding["symbol"] for holding in holdings] == ["8058"]
    assert "user_id" not in holdings[0]
    assert summary_result.structured_content["total_cost"] == 300000
    assert dividends_result.structured_content["result"] == [
        {"year": 2024, "month": 3, "total_dividend": 1500.0}
    ]

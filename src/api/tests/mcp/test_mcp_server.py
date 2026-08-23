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

TRANSACTION_HISTORY_FIELDS = {
    "symbol",
    "stock_name",
    "transaction_type",
    "quantity",
    "price",
    "usd_price",
    "adjusted_price",
    "adjusted_quantity",
    "account_type",
    "fee",
    "tax",
    "realized_pl",
    "transaction_date",
}
DIVIDEND_HISTORY_FIELDS = {
    "symbol",
    "stock_name",
    "payment_date",
    "shares_owned",
    "total_amount",
    "tax",
    "fee",
    "net_amount",
}


async def _create_user(engine: AsyncEngine, username: str, email: str) -> AccessIdentity:
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await UserService(session).create_user(UserBase(username=username, email=email))
        await session.commit()
    return AccessIdentity(email=email)


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
    identity = AccessIdentity(email="unknown@example.com")
    transport = httpx2.ASGITransport(app=_mcp_app(setup_database, identity))

    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Cf-Access-Jwt-Assertion": "test-token"},
    ) as client:
        response = await client.post("/mcp", json={})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_mcp_exposes_read_only_tools_with_fixed_schemas_and_holding_sorting(
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
    await create_transaction(
        {
            "symbol": "AAPL",
            "transaction_type": "buy",
            "quantity": 10,
            "price": 36000,
            "usd_price": 240,
            "account_type": "特定",
            "fee": 0,
            "tax": 0,
            "transaction_date": "2024-01-01T00:00:00+09:00",
        }
    )

    assert (await client.post("/api/v1/holdings/8058/recalculate")).status_code == 200
    assert (await client.post("/api/v1/holdings/AAPL/recalculate")).status_code == 200
    await create_dividend(
        {
            "symbol": "8058",
            "payment_date": "2024-03-01T00:00:00+09:00",
            "shares_owned": 100,
            "total_amount": 15000,
            "tax": 4000,
            "fee": 1000,
        }
    )

    other_identity = await _create_user(setup_database, "other-user", "other@example.com")
    api_app.dependency_overrides[get_access_identity] = lambda: other_identity
    response = await client.post(
        "/api/v1/transactions/",
        json={
            "symbol": "AAPL",
            "transaction_type": "buy",
            "quantity": 1000,
            "price": 36000,
            "usd_price": 240,
            "account_type": "NISA(成長投資枠)",
            "fee": 0,
            "tax": 0,
            "transaction_date": "2024-01-01T00:00:00+09:00",
        },
    )
    assert response.status_code == 200
    response = await client.post(
        "/api/v1/dividends/",
        json={
            "symbol": "AAPL",
            "payment_date": "2024-04-02T00:00:00+09:00",
            "shares_owned": 1000,
            "total_amount": 99999,
            "tax": 0,
            "fee": 0,
        },
    )
    assert response.status_code == 200
    api_app.dependency_overrides[get_access_identity] = lambda: auth_user

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
        results = {}
        for sort_by in (
            "market_value",
            "unrealized_pl",
            "unrealized_pl_percentage",
            "total_pl",
            "total_pl_percentage",
        ):
            for order in ("asc", "desc"):
                results[(sort_by, order)] = await mcp_client.call_tool(
                    "list_holdings",
                    {"sort_by": sort_by, "order": order},
                )
        detail_result = await mcp_client.call_tool("get_holding", {"symbol": " aapl "})
        transactions_result = await mcp_client.call_tool("list_transactions", {"limit": 1})
        filtered_transactions_result = await mcp_client.call_tool("list_transactions", {"symbol": " 8058 "})
        dividends_result = await mcp_client.call_tool("list_dividends", {"limit": 1})
        filtered_dividends_result = await mcp_client.call_tool("list_dividends", {"symbol": " aapl "})

        sell_response = await client.post(
            "/api/v1/transactions/",
            json={
                "symbol": "8058",
                "transaction_type": "sell",
                "quantity": 100,
                "price": 3200,
                "account_type": "NISA(成長投資枠)",
                "fee": 0,
                "tax": 0,
                "transaction_date": "2024-04-01T00:00:00+09:00",
            },
        )
        assert sell_response.status_code == 200
        sell_response = await client.post(
            "/api/v1/transactions/",
            json={
                "symbol": "AAPL",
                "transaction_type": "sell",
                "quantity": 10,
                "price": 40000,
                "usd_price": 260,
                "account_type": "特定",
                "fee": 0,
                "tax": 0,
                "transaction_date": "2024-04-01T00:00:00+09:00",
            },
        )
        assert sell_response.status_code == 200
        sold_holdings_result = await mcp_client.call_tool("list_holdings")
        sold_detail_result = await mcp_client.call_tool("get_holding", {"symbol": "8058"})
        other_user_detail_result = await mcp_client.call_tool("get_holding", {"symbol": "AAPL"})

    tools_by_name = {tool.name: tool for tool in tools.tools}
    assert set(tools_by_name) == {
        "list_holdings",
        "get_holding",
        "list_transactions",
        "list_dividends",
    }
    assert all(tool.annotations and tool.annotations.read_only_hint for tool in tools.tools)

    list_tool = tools_by_name["list_holdings"]
    assert set(list_tool.input_schema["properties"]) == {"sort_by", "order"}
    assert list_tool.input_schema["properties"]["sort_by"]["default"] == "market_value"
    assert list_tool.input_schema["properties"]["order"]["default"] == "desc"
    assert set(list_tool.input_schema["properties"]["sort_by"]["enum"]) == {
        "market_value",
        "unrealized_pl",
        "unrealized_pl_percentage",
        "total_pl",
        "total_pl_percentage",
    }
    assert set(list_tool.input_schema["properties"]["order"]["enum"]) == {"asc", "desc"}
    assert set(list_tool.output_schema["properties"]) == {"holdings"}
    item_reference = list_tool.output_schema["properties"]["holdings"]["items"]["$ref"]
    item_schema = list_tool.output_schema["$defs"][item_reference.rsplit("/", maxsplit=1)[-1]]
    expected_list_fields = {
        "symbol",
        "stock_name",
        "market_value",
        "unrealized_pl",
        "unrealized_pl_percentage",
        "total_pl",
        "total_pl_percentage",
    }
    assert set(item_schema["properties"]) == expected_list_fields

    history_tool_fields = {
        "list_transactions": TRANSACTION_HISTORY_FIELDS,
        "list_dividends": DIVIDEND_HISTORY_FIELDS,
    }
    for tool_name, expected_fields in history_tool_fields.items():
        history_tool = tools_by_name[tool_name]
        input_properties = history_tool.input_schema["properties"]
        assert set(input_properties) == {"limit", "symbol"}
        assert input_properties["limit"]["default"] == 20
        assert input_properties["limit"]["minimum"] == 1
        assert input_properties["limit"]["maximum"] == 100
        assert input_properties["symbol"]["default"] is None

        collection_name = tool_name.removeprefix("list_")
        assert set(history_tool.output_schema["properties"]) == {collection_name}
        item_reference = history_tool.output_schema["properties"][collection_name]["items"]["$ref"]
        item_schema = history_tool.output_schema["$defs"][item_reference.rsplit("/", maxsplit=1)[-1]]
        assert set(item_schema["properties"]) == expected_fields
        assert set(item_schema["required"]) == expected_fields

    descending_expectations = {
        "market_value": ["AAPL", "8058"],
        "unrealized_pl": ["AAPL", "8058"],
        "unrealized_pl_percentage": ["AAPL", "8058"],
        "total_pl": ["8058", "AAPL"],
        "total_pl_percentage": ["8058", "AAPL"],
    }
    for sort_by, expected_symbols in descending_expectations.items():
        descending = results[(sort_by, "desc")].structured_content["holdings"]
        ascending = results[(sort_by, "asc")].structured_content["holdings"]
        assert [holding["symbol"] for holding in descending] == expected_symbols
        assert [holding["symbol"] for holding in ascending] == list(reversed(expected_symbols))
        assert set(descending[0]) == expected_list_fields
        assert "result" not in results[(sort_by, "desc")].structured_content

    detail = detail_result.structured_content
    expected_detail_fields = {
        "symbol",
        "stock_name",
        "security_type",
        "currency",
        "country",
        "sector_name",
        "quantity",
        "average_cost",
        "total_cost",
        "current_price",
        "current_price_usd",
        "market_value",
        "market_value_usd",
        "unrealized_pl",
        "unrealized_pl_percentage",
        "realized_pl",
        "total_dividend",
        "total_pl",
        "total_pl_percentage",
        "account_holdings",
        "note",
        "last_updated",
    }
    assert set(tools_by_name["get_holding"].output_schema["properties"]) == expected_detail_fields
    assert set(detail) == expected_detail_fields
    assert detail["symbol"] == "AAPL"
    assert detail["quantity"] == 10
    assert detail["account_holdings"] == [{"account_type": "特定", "quantity": 10.0}]
    assert detail["last_updated"].endswith("+09:00")
    assert "user_id" not in detail
    assert sold_holdings_result.structured_content == {"holdings": []}
    assert sold_detail_result.is_error
    assert other_user_detail_result.is_error

    transactions = transactions_result.structured_content["transactions"]
    assert len(transactions) == 1
    assert set(transactions[0]) == TRANSACTION_HISTORY_FIELDS
    assert transactions[0]["symbol"] == "AAPL"
    assert transactions[0]["quantity"] == 10
    assert transactions[0]["transaction_date"].endswith("+09:00")
    assert filtered_transactions_result.structured_content["transactions"][0]["symbol"] == "8058"

    dividends = dividends_result.structured_content["dividends"]
    assert len(dividends) == 1
    assert set(dividends[0]) == DIVIDEND_HISTORY_FIELDS
    assert dividends[0]["symbol"] == "8058"
    assert dividends[0]["net_amount"] == 10000
    assert dividends[0]["payment_date"].endswith("+09:00")
    assert filtered_dividends_result.structured_content == {"dividends": []}

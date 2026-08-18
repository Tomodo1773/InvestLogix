"""ユーザー設定APIのテスト。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_update_slack_user_id(client: AsyncClient, auth_user) -> None:
    response = await client.put(
        "/api/v1/users/me/slack-user-id",
        json={"slack_user_id": "U1234567890"},
    )

    assert response.status_code == 200
    assert response.json()["slack_user_id"] == "U1234567890"


@pytest.mark.asyncio
async def test_update_slack_user_id_rejects_empty_value(client: AsyncClient, auth_user) -> None:
    response = await client.put(
        "/api/v1/users/me/slack-user-id",
        json={"slack_user_id": ""},
    )

    assert response.status_code == 422

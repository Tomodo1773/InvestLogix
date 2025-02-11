import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """
    ルートエンドポイントのテスト
    - 期待する動作:
        - ステータスコード200
        - APIの基本情報を含むレスポンス
    """
    response = await client.get("/api/v1/")
    assert response.status_code == 200
    assert response.json() == {
        "name": "InvestLogix API",
        "version": "1.0.0",
        "description": "株式投資ポートフォリオ管理APIサービス",
    }


def test_root_endpoint_sync(sync_client: TestClient):
    """
    ルートエンドポイントの同期的なテスト
    - 期待する動作:
        - ステータスコード200
        - APIの基本情報を含むレスポンス
    """
    response = sync_client.get("/api/v1/")
    assert response.status_code == 200
    assert response.json() == {
        "name": "InvestLogix API",
        "version": "1.0.0",
        "description": "株式投資ポートフォリオ管理APIサービス",
    }

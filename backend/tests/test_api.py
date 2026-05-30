"""API 集成测试 (MongoDB 版)"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport


@pytest_asyncio.fixture
async def client():
    """创建测试客户端，mock 掉 MongoDB 连接"""
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    mock_cursor.limit = MagicMock(return_value=mock_cursor)

    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)
    mock_collection.find_one = AsyncMock(return_value=None)
    mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="test"))

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    with patch("app.core.database.connect_db", new_callable=AsyncMock), \
         patch("app.core.database.close_db", new_callable=AsyncMock), \
         patch("app.core.database.get_database", return_value=mock_db):

        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Personal Agent Team"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_list_tasks(client):
    response = await client.get("/api/v1/tasks")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert "total" in data

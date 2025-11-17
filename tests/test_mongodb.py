import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_mongodb_filter_endpoint():
    """Test MongoDB advanced filtering with multiple query parameters."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/mongodb/products/filter", params={"status": "active", "limit": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # If data exists, verify fields
        if data:
            first = data[0]
            assert "title" in first and "status" in first

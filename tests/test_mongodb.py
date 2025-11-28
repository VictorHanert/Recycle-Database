import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.mongodb import get_mongodb_client

@pytest.mark.asyncio
async def test_mongodb_filter_endpoint():
    """Test MongoDB advanced filtering with multiple query parameters."""
    # Skip if MongoDB not available
    try:
        client = get_mongodb_client()
        await client.admin.command('ping')
    except Exception:
        pytest.skip("MongoDB connection unavailable")
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/mongodb/products/filter", params={"status": "active", "limit": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # If data exists, verify fields
        if data:
            first = data[0]
            assert "title" in first and "status" in first

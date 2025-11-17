import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_mysql_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["databases"]["mysql_configured"] is True

@pytest.mark.asyncio
async def test_mysql_products_list():
    """Test MySQL products list endpoint"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/products", follow_redirects=True)
        assert resp.status_code == 200
        data = resp.json()
        assert "products" in data
        assert isinstance(data["products"], list)

@pytest.mark.asyncio
async def test_mysql_stored_procedure_popular_products():
    """Test stored procedure via activity endpoint (uses vw_popular_products view)"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/activity/popular-products", params={"limit": 5})
        assert resp.status_code == 200
        data = resp.json()
        # Response is paginated with products key
        assert "products" in data
        assert isinstance(data["products"], list)
        # If data exists, verify expected fields from view
        if data["products"]:
            assert "id" in data["products"][0]
            assert "title" in data["products"][0]

@pytest.mark.asyncio
async def test_mysql_locations():
    """Test MySQL locations endpoint"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/locations", follow_redirects=True)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

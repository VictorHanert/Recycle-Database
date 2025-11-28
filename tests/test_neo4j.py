import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.neo4j import get_neo4j_driver

@pytest.mark.asyncio
async def test_neo4j_recommendations_endpoint():
    # Skip if Neo4j not available
    try:
        driver = await get_neo4j_driver()
        await driver.verify_connectivity()
    except Exception:
        pytest.skip("Neo4j connection unavailable")
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Use popular endpoint to get an existing product id
        popular_resp = await client.get("/neo4j/products/popular", params={"limit": 1})
        assert popular_resp.status_code == 200
        popular = popular_resp.json()
        if not popular:
            pytest.skip("No products available in Neo4j to test recommendations")
        product_id = popular[0]["id"]
        rec_resp = await client.get(f"/neo4j/products/{product_id}/recommendations", params={"limit": 5})
        assert rec_resp.status_code == 200
        recs = rec_resp.json()
        assert isinstance(recs, list)
        # If recommendations exist ensure score present
        if recs:
            assert "recommendation_score" in recs[0]

"""Neo4j Product repository (async)."""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
from neo4j import AsyncSession


class Neo4jProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, title: str, description: Optional[str], price_amount: float, seller_username: str) -> Dict[str, Any]:
        product_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        query = (
            "MERGE (u:User {username: $username}) "
            "CREATE (p:Product {id: $id, title: $title, description: $description, price_amount: $price_amount, status: 'active', view_count: 0, favorite_count: 0, created_at: $created_at}) "
            "MERGE (u)-[:CREATED {at: $created_at}]->(p) "
            "RETURN p"
        )
        result = await self.session.run(
            query,
            username=seller_username,
            id=product_id,
            title=title,
            description=description,
            price_amount=price_amount,
            created_at=created_at,
        )
        record = await result.single()
        return record["p"]._properties if record else {}

    async def get_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        result = await self.session.run("MATCH (p:Product {id: $id}) RETURN p", id=product_id)
        record = await result.single()
        return record["p"]._properties if record else None

    async def list(self, skip: int = 0, limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if status:
            query = "MATCH (p:Product {status: $status}) RETURN p ORDER BY p.created_at DESC SKIP $skip LIMIT $limit"
            result = await self.session.run(query, status=status, skip=skip, limit=limit)
        else:
            result = await self.session.run(
                "MATCH (p:Product) RETURN p ORDER BY p.created_at DESC SKIP $skip LIMIT $limit",
                skip=skip,
                limit=limit,
            )
        records = []
        async for rec in result:
            records.append(rec["p"]._properties)
        return records

    async def popular(self, limit: int = 10) -> List[Dict[str, Any]]:
        result = await self.session.run(
            "MATCH (p:Product) RETURN p ORDER BY p.view_count DESC LIMIT $limit", limit=limit
        )
        records = []
        async for rec in result:
            records.append(rec["p"]._properties)
        return records

    async def add_favorite(self, username: str, product_id: str) -> bool:
        query = (
            "MATCH (u:User {username: $username}), (p:Product {id: $product_id}) "
            "MERGE (u)-[:FAVORITED {at: $now}]->(p) "
            "SET p.favorite_count = coalesce(p.favorite_count, 0) + 1 "
            "RETURN p"
        )
        now = datetime.now(timezone.utc).isoformat()
        result = await self.session.run(query, username=username, product_id=product_id, now=now)
        rec = await result.single()
        return rec is not None

    async def add_view(self, username: str, product_id: str) -> bool:
        query = (
            "MATCH (u:User {username: $username}), (p:Product {id: $product_id}) "
            "MERGE (u)-[:VIEWED {at: $now}]->(p) "
            "SET p.view_count = coalesce(p.view_count, 0) + 1 "
            "RETURN p"
        )
        now = datetime.now(timezone.utc).isoformat()
        result = await self.session.run(query, username=username, product_id=product_id, now=now)
        rec = await result.single()
        return rec is not None

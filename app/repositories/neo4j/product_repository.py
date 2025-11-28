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

    async def recommendations(self, product_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recommend products based on shared FAVORITED or VIEWED users.

        Strategy: Find users who FAVORITED or VIEWED the target product, then other products
        those users also FAVORITED or VIEWED. Rank by distinct user overlap.
        """
        query = (
            "MATCH (target:Product {id: $id})<-[:FAVORITED|:VIEWED]-(u:User)-[:FAVORITED|:VIEWED]->(other:Product) "
            "WHERE other.id <> $id "
            "WITH other, count(DISTINCT u) AS score "
            "WHERE score > 0 "
            "RETURN other, score ORDER BY score DESC, other.created_at DESC LIMIT $limit"
        )
        result = await self.session.run(query, id=product_id, limit=limit)
        recommendations: List[Dict[str, Any]] = []
        async for rec in result:
            props = rec["other"]._properties
            props["recommendation_score"] = rec["score"]
            recommendations.append(props)
        return recommendations

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
    
    async def update(
        self, 
        product_id: str, 
        title: Optional[str] = None,
        description: Optional[str] = None,
        price_amount: Optional[float] = None,
        status: Optional[str] = None,
        condition: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update product properties in Neo4j."""
        # Build SET clause dynamically
        set_parts = []
        params = {"id": product_id, "updated_at": datetime.now(timezone.utc).isoformat()}
        
        if title is not None:
            set_parts.append("p.title = $title")
            params["title"] = title
        if description is not None:
            set_parts.append("p.description = $description")
            params["description"] = description
        if price_amount is not None:
            set_parts.append("p.price_amount = $price_amount")
            params["price_amount"] = price_amount
        if status is not None:
            set_parts.append("p.status = $status")
            params["status"] = status
        if condition is not None:
            set_parts.append("p.condition = $condition")
            params["condition"] = condition
        
        if not set_parts:
            return await self.get_by_id(product_id)
        
        set_parts.append("p.updated_at = $updated_at")
        set_clause = ", ".join(set_parts)
        
        query = f"MATCH (p:Product {{id: $id}}) SET {set_clause} RETURN p"
        result = await self.session.run(query, **params)
        record = await result.single()
        return record["p"]._properties if record else None
    
    async def delete(self, product_id: str) -> bool:
        """Delete product node and all its relationships."""
        query = (
            "MATCH (p:Product {id: $id}) "
            "DETACH DELETE p "
            "RETURN count(p) as deleted"
        )
        result = await self.session.run(query, id=product_id)
        record = await result.single()
        return record and record["deleted"] > 0
    
    async def mark_as_sold(self, product_id: str) -> bool:
        """Mark product as sold by updating status property."""
        query = (
            "MATCH (p:Product {id: $id}) "
            "SET p.status = 'sold', p.updated_at = $updated_at "
            "RETURN p"
        )
        result = await self.session.run(
            query, 
            id=product_id, 
            updated_at=datetime.now(timezone.utc).isoformat()
        )
        record = await result.single()
        return record is not None
    
    async def toggle_status(self, product_id: str) -> Optional[str]:
        """Toggle product status between active and paused. Returns new status."""
        # Get current status
        product = await self.get_by_id(product_id)
        if not product:
            return None
        
        current_status = product.get("status", "active")
        new_status = "paused" if current_status == "active" else "active"
        
        query = (
            "MATCH (p:Product {id: $id}) "
            "SET p.status = $status, p.updated_at = $updated_at "
            "RETURN p"
        )
        result = await self.session.run(
            query,
            id=product_id,
            status=new_status,
            updated_at=datetime.now(timezone.utc).isoformat()
        )
        record = await result.single()
        return new_status if record else None
    
    async def track_view(self, product_id: str, viewer_username: Optional[str] = None) -> bool:
        """
        Track product view by incrementing counter and optionally creating VIEWED relationship.
        If viewer is anonymous, just increment counter.
        """
        if viewer_username:
            # Create VIEWED relationship and increment counter
            return await self.add_view(viewer_username, product_id)
        else:
            # Just increment counter for anonymous views
            query = (
                "MATCH (p:Product {id: $id}) "
                "SET p.view_count = coalesce(p.view_count, 0) + 1 "
                "RETURN p"
            )
            result = await self.session.run(query, id=product_id)
            record = await result.single()
            return record is not None
    
    async def get_seller_username(self, product_id: str) -> Optional[str]:
        """Get the username of the product seller via CREATED relationship."""
        query = (
            "MATCH (u:User)-[:CREATED]->(p:Product {id: $id}) "
            "RETURN u.username as username"
        )
        result = await self.session.run(query, id=product_id)
        record = await result.single()
        return record["username"] if record else None

"""Neo4j User repository (async)."""
from typing import Optional, List, Dict, Any
from neo4j import AsyncSession


class Neo4jUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, username: str, email: Optional[str] = None, full_name: Optional[str] = None) -> Dict[str, Any]:
        query = (
            "MERGE (u:User {username: $username}) "
            "ON CREATE SET u.email = $email, u.full_name = $full_name "
            "RETURN u"
        )
        result = await self.session.run(query, username=username, email=email, full_name=full_name)
        record = await result.single()
        return record["u"]._properties if record else {}

    async def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        result = await self.session.run("MATCH (u:User {username: $username}) RETURN u", username=username)
        record = await result.single()
        return record["u"]._properties if record else None

    async def list_users(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        result = await self.session.run(
            "MATCH (u:User) RETURN u SKIP $skip LIMIT $limit", skip=skip, limit=limit
        )
        return [rec["u"]._properties for rec in await result.to_list()]

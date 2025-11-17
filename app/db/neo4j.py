"""Neo4j async connection utilities and initialization."""
from typing import Optional, AsyncIterator
from contextlib import asynccontextmanager

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import get_settings
import asyncio

_driver: Optional[AsyncDriver] = None


def get_neo4j_settings():
    settings = get_settings()
    return settings.neo4j_url, settings.neo4j_user, settings.neo4j_password


async def get_neo4j_driver() -> AsyncDriver:
    """Singleton async driver for Neo4j."""
    global _driver
    if _driver is None:
        url, user, password = get_neo4j_settings()
        _driver = AsyncGraphDatabase.driver(url, auth=(user, password))
    return _driver


@asynccontextmanager
async def neo4j_session() -> AsyncIterator:
    """Provide an async Neo4j session via context manager."""
    driver = await get_neo4j_driver()
    session = driver.session()
    try:
        yield session
    finally:
        await session.close()


async def init_neo4j():
    """Initialize Neo4j constraints and indexes with simple retry."""
    driver = await get_neo4j_driver()
    last_exc: Exception | None = None
    for _ in range(20):
        try:
            async with driver.session() as session:
                await session.run(
                    "CREATE CONSTRAINT user_username IF NOT EXISTS FOR (u:User) REQUIRE u.username IS UNIQUE"
                )
                await session.run(
                    "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE"
                )
                await session.run(
                    "CREATE INDEX product_status IF NOT EXISTS FOR (p:Product) ON (p.status)"
                )
            return
        except Exception as exc:  # pragma: no cover
            last_exc = exc
            await asyncio.sleep(1)
    if last_exc:
        raise last_exc


async def close_neo4j():
    """Close Neo4j driver on shutdown."""
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None

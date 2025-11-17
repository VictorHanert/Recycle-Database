import asyncio
import sys
from pathlib import Path
from typing import Any
from datetime import timezone

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.mysql import SessionLocal
from app.db.neo4j import get_neo4j_driver, init_neo4j
from neo4j import AsyncDriver
from app.models.user import User
from app.models.product import Product
from app.models.favorites import Favorite


async def migrate_users(session_mysql) -> int:
    driver: AsyncDriver = await get_neo4j_driver()
    count = 0

    users = session_mysql.query(User).all()

    async with driver.session() as session:
        for u in users:
            await session.run(
                (
                    "MERGE (u:User {username: $username}) "
                    "ON CREATE SET u.email = $email, u.full_name = $full_name"
                ),
                username=u.username,
                email=u.email,
                full_name=u.full_name or u.username,
            )
            count += 1

    return count


async def migrate_products(session_mysql) -> int:
    driver: AsyncDriver = await get_neo4j_driver()
    count = 0

    products = session_mysql.query(Product).all()

    async with driver.session() as session:
        for p in products:
            seller = session_mysql.get(User, p.seller_id)
            if not seller:
                continue

            await session.run(
                (
                    "MERGE (u:User {username: $username}) "
                    "MERGE (p:Product {id: $id}) "
                    "SET p.title = $title, p.description = $description, p.price_amount = $price_amount, "
                    "    p.status = $status, p.view_count = coalesce($view_count, 0), p.favorite_count = coalesce($favorite_count, 0), "
                    "    p.created_at = $created_at "
                    "MERGE (u)-[:CREATED]->(p)"
                ),
                username=seller.username,
                id=str(p.id),
                title=p.title,
                description=p.description,
                price_amount=float(p.price_amount) if p.price_amount is not None else 0.0,
                status=str(p.status),
                view_count=int(p.views_count or 0),
                favorite_count=int(p.likes_count or 0),
                created_at=p.created_at.astimezone(timezone.utc).isoformat() if p.created_at else None,
            )
            count += 1

    return count


async def migrate_favorites(session_mysql) -> int:
    driver: AsyncDriver = await get_neo4j_driver()
    count = 0

    favorites = session_mysql.query(Favorite).all()

    async with driver.session() as session:
        for fav in favorites:
            user = session_mysql.get(User, fav.user_id)
            prod = session_mysql.get(Product, fav.product_id)
            if not user or not prod:
                continue

            await session.run(
                (
                    "MATCH (u:User {username: $username}), (p:Product {id: $product_id}) "
                    "MERGE (u)-[:FAVORITED]->(p)"
                ),
                username=user.username,
                product_id=str(prod.id),
            )
            count += 1

    return count


async def migrate_to_neo4j():
    await init_neo4j()

    session_mysql = SessionLocal()
    try:
        users_count = await migrate_users(session_mysql)
        products_count = await migrate_products(session_mysql)
        favorites_count = await migrate_favorites(session_mysql)
        print(
            f"Neo4j migration complete: {users_count} users, {products_count} products, {favorites_count} favorites"
        )
    finally:
        session_mysql.close()


if __name__ == "__main__":
    asyncio.run(migrate_to_neo4j())

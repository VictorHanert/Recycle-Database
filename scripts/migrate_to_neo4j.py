"""MySQL → Neo4j migration."""
import asyncio
import sys
from pathlib import Path
from typing import Any
from datetime import timezone

from sqlalchemy import create_engine, MetaData, select, func
from sqlalchemy.orm import sessionmaker
from neo4j import AsyncDriver

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.neo4j import get_neo4j_driver, init_neo4j
from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

metadata = MetaData()
metadata.reflect(engine, only=[
    "users",
    "products",
    "categories",
    "locations",
    "favorites",
    "item_views",
    "conversations",
    "conversation_participants",
    "messages",
])
users_t = metadata.tables["users"]
products_t = metadata.tables["products"]
categories_t = metadata.tables["categories"]
locations_t = metadata.tables["locations"]
favorites_t = metadata.tables["favorites"]
item_views_t = metadata.tables["item_views"]
conversations_t = metadata.tables["conversations"]
conversation_participants_t = metadata.tables["conversation_participants"]
messages_t = metadata.tables["messages"]


async def migrate_users(session_mysql) -> int:
    driver: AsyncDriver = await get_neo4j_driver()
    count = 0

    users = session_mysql.execute(select(users_t)).all()
    locations = {l.id: l for l in session_mysql.execute(select(locations_t)).all()}

    async with driver.session() as session:
        for u in users:
            loc_props: dict[str, Any] = {}
            if u.location_id and u.location_id in locations:
                loc = locations[u.location_id]
                loc_props = {
                    "city": loc.city,
                    "postcode": loc.postcode,
                    "country": "Denmark",
                }
                await session.run(
                    "MERGE (l:Location {postcode: $postcode, city: $city}) SET l.country = $country",
                    **loc_props
                )
            query = (
                "MERGE (u:User {username: $username}) SET u.email = $email, u.full_name = $full_name, u.is_active = $is_active"
            )
            params = {
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name or u.username,
                "is_active": bool(u.is_active),
            }
            if loc_props:
                query += " WITH u MATCH (l:Location {postcode: $postcode, city: $city}) MERGE (u)-[:LIVES_IN]->(l)"
                params.update(loc_props)
            await session.run(query, **params)
            count += 1
    return count


async def migrate_products(session_mysql) -> int:
    driver: AsyncDriver = await get_neo4j_driver()
    count = 0
    products = session_mysql.execute(select(products_t)).all()
    categories = {c.id: c for c in session_mysql.execute(select(categories_t)).all()}
    locations = {l.id: l for l in session_mysql.execute(select(locations_t)).all()}
    async with driver.session() as session:
        for p in products:
            seller = session_mysql.execute(select(users_t).where(users_t.c.id == p.seller_id)).first()
            if not seller:
                continue
            if p.category_id and p.category_id in categories:
                cat = categories[p.category_id]
                await session.run(
                    "MERGE (c:Category {id: $id}) SET c.name = $name",
                    id=str(cat.id),
                    name=cat.name
                )
            if p.location_id and p.location_id in locations:
                loc = locations[p.location_id]
                await session.run(
                    "MERGE (l:Location {postcode: $postcode, city: $city}) SET l.country = $country",
                    postcode=loc.postcode,
                    city=loc.city,
                    country="Denmark"
                )
            query = (
                "MERGE (u:User {username: $username}) MERGE (p:Product {id: $id}) SET p.title = $title, p.description = $description, "
                "p.price_amount = $price_amount, p.status = $status, p.view_count = coalesce($view_count,0), "
                "p.favorite_count = coalesce($favorite_count,0), p.created_at = $created_at MERGE (u)-[:CREATED]->(p)"
            )
            params = {
                "username": seller.username,
                "id": str(p.id),
                "title": p.title,
                "description": p.description,
                "price_amount": float(p.price_amount) if p.price_amount is not None else 0.0,
                "status": str(p.status),
                "view_count": int(p.views_count or 0),
                "favorite_count": int(p.likes_count or 0),
                "created_at": p.created_at.astimezone(timezone.utc).isoformat() if getattr(p, "created_at", None) else None,
            }
            if p.category_id and p.category_id in categories:
                query += " WITH p MATCH (c:Category {id: $category_id}) MERGE (p)-[:IN_CATEGORY]->(c)"
                params["category_id"] = str(p.category_id)
            if p.location_id and p.location_id in locations:
                loc = locations[p.location_id]
                query += " WITH p MATCH (l:Location {postcode: $postcode, city: $city}) MERGE (p)-[:LOCATED_IN]->(l)"
                params["postcode"] = loc.postcode
                params["city"] = loc.city
            await session.run(query, **params)
            count += 1
    return count


async def migrate_favorites(session_mysql) -> int:
    driver: AsyncDriver = await get_neo4j_driver()
    count = 0
    favorites = session_mysql.execute(select(favorites_t)).all()
    async with driver.session() as session:
        for fav in favorites:
            user = session_mysql.execute(select(users_t).where(users_t.c.id == fav.user_id)).first()
            prod = session_mysql.execute(select(products_t).where(products_t.c.id == fav.product_id)).first()
            if not user or not prod:
                continue
            await session.run(
                "MATCH (u:User {username: $username}), (p:Product {id: $product_id}) MERGE (u)-[:FAVORITED]->(p)",
                username=user.username,
                product_id=str(prod.id),
            )
            count += 1
    return count


async def migrate_item_views(session_mysql) -> int:
    driver: AsyncDriver = await get_neo4j_driver()
    count = 0
    item_views = session_mysql.execute(
        select(item_views_t)
        .where(item_views_t.c.viewer_user_id.isnot(None))
        .order_by(item_views_t.c.viewed_at.desc())
        .limit(1000)
    ).all()
    async with driver.session() as session:
        for v in item_views:
            user = session_mysql.execute(select(users_t).where(users_t.c.id == v.viewer_user_id)).first()
            product = session_mysql.execute(select(products_t).where(products_t.c.id == v.product_id)).first()
            if not user or not product:
                continue
            await session.run(
                "MATCH (u:User {username: $username}), (p:Product {id: $product_id}) MERGE (u)-[r:VIEWED]->(p) SET r.viewed_at = $viewed_at",
                username=user.username,
                product_id=str(product.id),
                viewed_at=v.viewed_at.astimezone(timezone.utc).isoformat() if getattr(v, "viewed_at", None) else None,
            )
            count += 1
    return count


async def migrate_messages(session_mysql) -> int:
    driver: AsyncDriver = await get_neo4j_driver()
    count = 0
    conversations = session_mysql.execute(select(conversations_t)).all()
    async with driver.session() as session:
        for conv in conversations:
            participants_data = session_mysql.execute(
                select(conversation_participants_t).where(conversation_participants_t.c.conversation_id == conv.id)
            ).all()
            if len(participants_data) < 2:
                continue
            users = []
            for part in participants_data:
                user = session_mysql.execute(select(users_t).where(users_t.c.id == part.user_id)).first()
                if user:
                    users.append(user)
            if len(users) < 2:
                continue
            message_count = session_mysql.execute(
                select(func.count()).select_from(messages_t).where(messages_t.c.conversation_id == conv.id)
            ).scalar() or 0
            for i in range(len(users)):
                for j in range(i + 1, len(users)):
                    await session.run(
                        "MATCH (u1:User {username: $user1}), (u2:User {username: $user2}) MERGE (u1)-[r1:MESSAGED]->(u2) MERGE (u2)-[r2:MESSAGED]->(u1) SET r1.message_count=$message_count, r2.message_count=$message_count, r1.last_message_at=$created_at, r2.last_message_at=$created_at",
                        user1=users[i].username,
                        user2=users[j].username,
                        message_count=int(message_count),
                        created_at=conv.created_at.astimezone(timezone.utc).isoformat() if getattr(conv, "created_at", None) else None,
                    )
            count += 1
    return count


async def create_recommendation_relationships(session_mysql) -> int:
    """Create SIMILAR_TO relationships between products based on shared categories and favorited by same users."""
    driver: AsyncDriver = await get_neo4j_driver()
    
    async with driver.session() as session:
        # Products in same category are similar
        result = await session.run(
            """
            MATCH (p1:Product)-[:IN_CATEGORY]->(c:Category)<-[:IN_CATEGORY]-(p2:Product)
            WHERE p1.id < p2.id
            MERGE (p1)-[r:SIMILAR_TO]-(p2)
            SET r.reason = 'same_category'
            RETURN count(r) as count
            """
        )
        record = await result.single()
        category_links = record["count"] if record else 0

        # Products favorited by same users are related
        result = await session.run(
            """
            MATCH (u:User)-[:FAVORITED]->(p1:Product)
            MATCH (u)-[:FAVORITED]->(p2:Product)
            WHERE p1.id < p2.id
            WITH p1, p2, count(u) as shared_users
            WHERE shared_users >= 2
            MERGE (p1)-[r:RELATED_TO]-(p2)
            SET r.shared_favorite_count = shared_users
            RETURN count(r) as count
            """
        )
        record = await result.single()
        favorite_links = record["count"] if record else 0

    return category_links + favorite_links


async def migrate_to_neo4j():
    await init_neo4j()

    session_mysql = SessionLocal()
    try:
        users_count = await migrate_users(session_mysql)
        products_count = await migrate_products(session_mysql)
        favorites_count = await migrate_favorites(session_mysql)
        views_count = await migrate_item_views(session_mysql)
        messages_count = await migrate_messages(session_mysql)
        recommendation_count = await create_recommendation_relationships(session_mysql)
        
        print(f"Neo4j migration complete:")
        print(f"  - {users_count} users (with LIVES_IN relationships)")
        print(f"  - {products_count} products (with CREATED, IN_CATEGORY, LOCATED_IN relationships)")
        print(f"  - {favorites_count} FAVORITED relationships")
        print(f"  - {views_count} VIEWED relationships")
        print(f"  - {messages_count} MESSAGED relationships")
        print(f"  - {recommendation_count} SIMILAR_TO/RELATED_TO relationships")
    finally:
        session_mysql.close()


if __name__ == "__main__":
    asyncio.run(migrate_to_neo4j())

import asyncio
import sys
from pathlib import Path
from typing import Any
from datetime import timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.neo4j import get_neo4j_driver, init_neo4j
from app.config import get_settings
from neo4j import AsyncDriver
from app.models.user import User
from app.models.product import Product
from app.models.favorites import Favorite
from app.models.category import Category
from app.models.location import Location
from app.models.item_views import ItemView
from app.models.messages import Message, Conversation, ConversationParticipant

settings = get_settings()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def migrate_users(session_mysql) -> int:
    driver: AsyncDriver = await get_neo4j_driver()
    count = 0

    users = session_mysql.query(User).all()
    locations = {l.id: l for l in session_mysql.query(Location).all()}

    async with driver.session() as session:
        for u in users:
            # Create location node if exists
            loc_props = {}
            if u.location_id and u.location_id in locations:
                loc = locations[u.location_id]
                loc_props = {
                    "city": loc.city,
                    "postcode": loc.postcode,
                    "country": "Denmark"
                }
                await session.run(
                    "MERGE (l:Location {postcode: $postcode, city: $city}) "
                    "SET l.country = $country",
                    **loc_props
                )
            
            # Create user and link to location
            query = "MERGE (u:User {username: $username}) SET u.email = $email, u.full_name = $full_name, u.is_active = $is_active"
            params = {
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name or u.username,
                "is_active": bool(u.is_active)
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

    products = session_mysql.query(Product).all()
    categories = {c.id: c for c in session_mysql.query(Category).all()}
    locations = {l.id: l for l in session_mysql.query(Location).all()}

    async with driver.session() as session:
        for p in products:
            seller = session_mysql.get(User, p.seller_id)
            if not seller:
                continue

            # Create category node if exists
            if p.category_id and p.category_id in categories:
                cat = categories[p.category_id]
                await session.run(
                    "MERGE (c:Category {id: $id}) SET c.name = $name",
                    id=str(cat.id),
                    name=cat.name
                )

            # Create location node if exists
            if p.location_id and p.location_id in locations:
                loc = locations[p.location_id]
                await session.run(
                    "MERGE (l:Location {postcode: $postcode, city: $city}) SET l.country = $country",
                    postcode=loc.postcode,
                    city=loc.city,
                    country="Denmark"
                )

            # Create product with relationships
            query = """
                MERGE (u:User {username: $username}) 
                MERGE (p:Product {id: $id}) 
                SET p.title = $title, p.description = $description, p.price_amount = $price_amount, 
                    p.status = $status, p.view_count = coalesce($view_count, 0), p.favorite_count = coalesce($favorite_count, 0), 
                    p.created_at = $created_at 
                MERGE (u)-[:CREATED]->(p)
            """
            params = {
                "username": seller.username,
                "id": str(p.id),
                "title": p.title,
                "description": p.description,
                "price_amount": float(p.price_amount) if p.price_amount is not None else 0.0,
                "status": str(p.status),
                "view_count": int(p.views_count or 0),
                "favorite_count": int(p.likes_count or 0),
                "created_at": p.created_at.astimezone(timezone.utc).isoformat() if p.created_at else None,
            }

            # Add category relationship
            if p.category_id and p.category_id in categories:
                query += " WITH p MATCH (c:Category {id: $category_id}) MERGE (p)-[:IN_CATEGORY]->(c)"
                params["category_id"] = str(p.category_id)

            # Add location relationship
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


async def migrate_item_views(session_mysql) -> int:
    """Migrate item views to create VIEWED relationships."""
    driver: AsyncDriver = await get_neo4j_driver()
    count = 0

    # Get item views (limit to avoid too many relationships) - only logged-in user views
    item_views = session_mysql.query(ItemView).filter(ItemView.viewer_user_id.isnot(None)).order_by(ItemView.viewed_at.desc()).limit(1000).all()

    async with driver.session() as session:
        for view in item_views:
            user = session_mysql.get(User, view.viewer_user_id)
            product = session_mysql.get(Product, view.product_id)
            
            if not user or not product:
                continue

            await session.run(
                """
                MATCH (u:User {username: $username}), (p:Product {id: $product_id})
                MERGE (u)-[r:VIEWED]->(p)
                SET r.viewed_at = $viewed_at
                """,
                username=user.username,
                product_id=str(product.id),
                viewed_at=view.viewed_at.astimezone(timezone.utc).isoformat() if view.viewed_at else None
            )
            count += 1

    return count


async def migrate_messages(session_mysql) -> int:
    """Migrate conversations to create MESSAGED relationships between users."""
    driver: AsyncDriver = await get_neo4j_driver()
    count = 0

    conversations = session_mysql.query(Conversation).all()

    async with driver.session() as session:
        for conv in conversations:
            # Get participants through the join table
            participants_data = session_mysql.query(ConversationParticipant).filter(
                ConversationParticipant.conversation_id == conv.id
            ).all()
            
            if len(participants_data) < 2:
                continue
            
            users = []
            for part in participants_data:
                user = session_mysql.get(User, part.user_id)
                if user:
                    users.append(user)
            
            if len(users) < 2:
                continue

            # Get message count for this conversation
            message_count = session_mysql.query(Message).filter(Message.conversation_id == conv.id).count()

            # Create bidirectional MESSAGED relationships between all participants
            for i in range(len(users)):
                for j in range(i + 1, len(users)):
                    await session.run(
                        """
                        MATCH (u1:User {username: $user1}), (u2:User {username: $user2})
                        MERGE (u1)-[r1:MESSAGED]->(u2)
                        MERGE (u2)-[r2:MESSAGED]->(u1)
                        SET r1.message_count = $message_count,
                            r2.message_count = $message_count,
                            r1.last_message_at = $created_at,
                            r2.last_message_at = $created_at
                        """,
                        user1=users[i].username,
                        user2=users[j].username,
                        message_count=message_count,
                        created_at=conv.created_at.astimezone(timezone.utc).isoformat() if conv.created_at else None
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

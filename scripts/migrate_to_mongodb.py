"""MySQL → MongoDB migration."""
import asyncio
import sys
from pathlib import Path
from typing import Any, Dict
from datetime import timezone

from sqlalchemy import create_engine, MetaData, select, func
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.mongodb import get_mongodb, init_mongodb
from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Reflect only required tables
metadata = MetaData()
metadata.reflect(engine, only=[
    "users",
    "products",
    "categories",
    "locations",
    "favorites",
    "item_views",
    "product_price_history",
    "conversations",
    "conversation_participants",
    "messages",
    "message_reads",
])
users_t = metadata.tables["users"]
products_t = metadata.tables["products"]
categories_t = metadata.tables["categories"]
locations_t = metadata.tables["locations"]
favorites_t = metadata.tables["favorites"]
item_views_t = metadata.tables["item_views"]
price_history_t = metadata.tables["product_price_history"]
conversations_t = metadata.tables["conversations"]
conversation_participants_t = metadata.tables["conversation_participants"]
messages_t = metadata.tables["messages"]
message_reads_t = metadata.tables["message_reads"]

def to_utc(dt):
    if dt is None:
        return None
    try:
        return dt.astimezone(timezone.utc)
    except Exception:
        return dt  # treat as already UTC


async def migrate_users(db_session) -> int:
    mongo = get_mongodb()
    count = 0

    users = db_session.execute(select(users_t)).all()

    for u in users:
        loc = None
        if u.location_id:
            loc_rec = db_session.execute(
                select(locations_t).where(locations_t.c.id == u.location_id)
            ).first()
            if loc_rec:
                loc = {
                    "city": loc_rec.city,
                    "postcode": loc_rec.postcode,
                    "country": "Denmark",
                }

        product_count = db_session.execute(
            select(func.count()).select_from(products_t).where(products_t.c.seller_id == u.id)
        ).scalar() or 0

        doc: Dict[str, Any] = {
            "username": u.username,
            "email": u.email,
            "hashed_password": u.hashed_password,
            "full_name": u.full_name or u.username,
            "phone": u.phone,
            "location": loc,
            "is_active": bool(u.is_active),
            "is_admin": bool(u.is_admin),
            "created_at": to_utc(u.created_at),
            "updated_at": to_utc(u.updated_at),
            "product_count": int(product_count),
        }

        await mongo.users.update_one({"username": u.username}, {"$set": doc}, upsert=True)
        count += 1

    return count


async def migrate_products(db_session) -> int:
    mongo = get_mongodb()
    count = 0

    categories = {c.id: c for c in db_session.execute(select(categories_t)).all()}
    locations = {l.id: l for l in db_session.execute(select(locations_t)).all()}
    products = db_session.execute(select(products_t)).all()

    for p in products:
        seller = db_session.execute(select(users_t).where(users_t.c.id == p.seller_id)).first()
        if not seller:
            continue

        seller_emb = {
            "id": str(seller.id),
            "username": seller.username,
            "full_name": seller.full_name or seller.username,
        }

        cat_emb = None
        if p.category_id and p.category_id in categories:
            cat = categories[p.category_id]
            parent_name = None
            if getattr(cat, "parent_id", None) in categories:
                parent_name = categories[cat.parent_id].name
            cat_emb = {"id": str(cat.id), "name": cat.name, "parent_name": parent_name}

        loc_emb = None
        if p.location_id and p.location_id in locations:
            loc = locations[p.location_id]
            loc_emb = {"city": loc.city, "postcode": loc.postcode, "country": "Denmark"}

        price_history = db_session.execute(
            select(price_history_t).where(price_history_t.c.product_id == p.id).order_by(price_history_t.c.changed_at)
        ).all()
        price_history_emb = [
            {
                "amount": float(ph.amount) if ph.amount is not None else 0.0,
                "currency": ph.currency or "DKK",
                "changed_at": to_utc(ph.changed_at),
            }
            for ph in price_history
        ]

        recent_views = db_session.execute(
            select(item_views_t)
            .where(item_views_t.c.product_id == p.id)
            .order_by(item_views_t.c.viewed_at.desc())
            .limit(10)
        ).all()
        views_emb = [
            {
                "viewer_user_id": str(v.viewer_user_id) if v.viewer_user_id else None,
                "viewed_at": to_utc(v.viewed_at),
            }
            for v in recent_views
        ]

        stats = {
            "view_count": int(p.views_count or 0),
            "favorite_count": int(p.likes_count or 0),
        }

        doc: Dict[str, Any] = {
            "legacy_mysql_id": int(p.id),
            "title": p.title,
            "description": p.description,
            "price_amount": float(p.price_amount) if p.price_amount is not None else 0.0,
            "price_currency": p.price_currency or "DKK",
            "product_condition": str(p.condition),
            "status": str(p.status),
            "seller": seller_emb,
            "category": cat_emb,
            "location": loc_emb,
            "details": {"colors": [], "materials": [], "tags": []},
            "images": [],
            "stats": stats,
            "price_history": price_history_emb,
            "recent_views": views_emb,
            "created_at": to_utc(p.created_at),
            "updated_at": to_utc(p.updated_at),
        }

        created_at_value = doc.pop("created_at", None)
        set_doc = {k: v for k, v in doc.items() if v is not None}

        await mongo.products.update_one(
            {"legacy_mysql_id": int(p.id)},
            {
                "$set": set_doc,
                "$setOnInsert": ({"created_at": created_at_value} if created_at_value is not None else {}),
            },
            upsert=True,
        )
        count += 1

    return count


async def migrate_conversations(db_session) -> int:
    mongo = get_mongodb()
    count = 0

    conversations = db_session.execute(select(conversations_t)).all()

    for conv in conversations:
        participants_data = db_session.execute(
            select(conversation_participants_t).where(conversation_participants_t.c.conversation_id == conv.id)
        ).all()
        if len(participants_data) < 2:
            continue

        participants_list = []
        for part in participants_data:
            user = db_session.execute(select(users_t).where(users_t.c.id == part.user_id)).first()
            if user:
                participants_list.append({"user_id": str(user.id), "username": user.username})

        messages = db_session.execute(
            select(messages_t).where(messages_t.c.conversation_id == conv.id).order_by(messages_t.c.created_at)
        ).all()
        messages_emb = []
        for msg in messages:
            sender = db_session.execute(select(users_t).where(users_t.c.id == msg.sender_id)).first()
            if sender:
                read_records = db_session.execute(
                    select(message_reads_t).where(message_reads_t.c.message_id == msg.id)
                ).all()
                is_read = len(read_records) > 0
                messages_emb.append({
                    "sender_id": str(msg.sender_id),
                    "sender_username": sender.username,
                    "body": msg.body,
                    "is_read": is_read,
                    "created_at": to_utc(msg.created_at),
                })

        doc = {
            "legacy_mysql_id": int(conv.id),
            "participants": participants_list,
            "product_id": str(conv.product_id) if conv.product_id else None,
            "messages": messages_emb,
            "message_count": len(messages_emb),
            "last_message_at": messages_emb[-1]["created_at"] if messages_emb else None,
            "created_at": to_utc(conv.created_at),
        }

        await mongo.conversations.update_one(
            {"legacy_mysql_id": int(conv.id)}, {"$set": doc}, upsert=True
        )
        count += 1

    return count


async def migrate_favorites(db_session) -> int:
    mongo = get_mongodb()
    favorites = db_session.execute(select(favorites_t)).all()
    user_favorites: Dict[int, list] = {}
    for fav in favorites:
        user_favorites.setdefault(fav.user_id, []).append(
            {
                "product_id": str(fav.product_id),
                "created_at": to_utc(fav.created_at),
            }
        )
    for user_id, favs in user_favorites.items():
        user = db_session.execute(select(users_t).where(users_t.c.id == user_id)).first()
        if user:
            await mongo.users.update_one(
                {"username": user.username},
                {"$set": {"favorites": favs, "favorite_count": len(favs)}},
            )
    return len(user_favorites)


async def migrate_to_mongodb():
    await init_mongodb()

    session = SessionLocal()
    try:
        users_count = await migrate_users(session)
        products_count = await migrate_products(session)
        conversations_count = await migrate_conversations(session)
        favorites_count = await migrate_favorites(session)
        
        print(f"MongoDB migration complete:")
        print(f"  - {users_count} users")
        print(f"  - {products_count} products (with price history and views)")
        print(f"  - {conversations_count} conversations (with embedded messages)")
        print(f"  - {favorites_count} users with favorites")
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(migrate_to_mongodb())

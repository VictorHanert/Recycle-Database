import asyncio
import sys
from pathlib import Path
from typing import Any, Dict

from datetime import timezone

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.mysql import SessionLocal
from app.db.mongodb import get_mongodb, init_mongodb
from app.models.user import User
from app.models.product import Product
from app.models.category import Category
from app.models.location import Location
from app.models.favorites import Favorite
from app.models.messages import Message, Conversation, ConversationParticipant, MessageRead
from app.models.item_views import ItemView
from app.models.price_history import ProductPriceHistory


async def migrate_users(db_session) -> int:
    mongo = get_mongodb()
    count = 0

    users = db_session.query(User).all()

    for u in users:
        loc = None
        if u.location_id:
            # Fetch location lazily if not loaded
            if isinstance(u.location, Location) and u.location is not None:
                loc = {"city": u.location.city, "postcode": u.location.postcode, "country": "Denmark"}
            else:
                loc_rec = db_session.get(Location, u.location_id)
                if loc_rec:
                    loc = {"city": loc_rec.city, "postcode": loc_rec.postcode, "country": "Denmark"}

        doc: Dict[str, Any] = {
            "username": u.username,
            "email": u.email,
            "hashed_password": u.hashed_password,
            "full_name": u.full_name or u.username,
            "phone": u.phone,
            "location": loc,
            "is_active": bool(u.is_active),
            "is_admin": bool(u.is_admin),
            "created_at": u.created_at.astimezone(timezone.utc) if u.created_at else None,
            "updated_at": u.updated_at.astimezone(timezone.utc) if u.updated_at else None,
            "product_count": len(u.products) if hasattr(u, "products") and u.products is not None else 0,
        }

        # Upsert by unique username
        await mongo.users.update_one({"username": u.username}, {"$set": doc}, upsert=True)
        count += 1

    return count


async def migrate_products(db_session) -> int:
    mongo = get_mongodb()
    count = 0

    # Build helper caches to minimize queries
    categories = {c.id: c for c in db_session.query(Category).all()}
    locations = {l.id: l for l in db_session.query(Location).all()}

    products = db_session.query(Product).all()

    for p in products:
        seller = db_session.get(User, p.seller_id)
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
            parent_name = categories[cat.parent_id].name if getattr(cat, "parent_id", None) in categories else None
            cat_emb = {"id": str(cat.id), "name": cat.name, "parent_name": parent_name}

        loc_emb = None
        if p.location_id and p.location_id in locations:
            loc = locations[p.location_id]
            loc_emb = {"city": loc.city, "postcode": loc.postcode, "country": "Denmark"}

        # Get price history for this product
        price_history = db_session.query(ProductPriceHistory).filter(ProductPriceHistory.product_id == p.id).order_by(ProductPriceHistory.changed_at).all()
        price_history_emb = [
            {
                "amount": float(ph.amount),
                "currency": ph.currency or "DKK",
                "changed_at": ph.changed_at.astimezone(timezone.utc) if ph.changed_at else None
            }
            for ph in price_history
        ]

        # Get recent views for this product (last 10)
        recent_views = db_session.query(ItemView).filter(ItemView.product_id == p.id).order_by(ItemView.viewed_at.desc()).limit(10).all()
        views_emb = [
            {
                "viewer_user_id": str(v.viewer_user_id) if v.viewer_user_id else None,
                "viewed_at": v.viewed_at.astimezone(timezone.utc) if v.viewed_at else None
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
            "created_at": p.created_at.astimezone(timezone.utc) if p.created_at else None,
            "updated_at": p.updated_at.astimezone(timezone.utc) if p.updated_at else None,
        }

        # Separate created_at to avoid conflict between $set and $setOnInsert
        created_at_value = doc.pop("created_at", None)
        # Remove None values from $set to keep document clean
        set_doc = {k: v for k, v in doc.items() if v is not None}

        # Upsert by legacy_mysql_id to avoid duplicates on re-run
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
    """Migrate conversations with embedded messages - demonstrates nested documents."""
    mongo = get_mongodb()
    count = 0

    conversations = db_session.query(Conversation).all()

    for conv in conversations:
        # Get participants through the relationship table
        participants_data = db_session.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conv.id
        ).all()
        
        if len(participants_data) < 2:
            continue  # Skip incomplete conversations
        
        participants_list = []
        for part in participants_data:
            user = db_session.get(User, part.user_id)
            if user:
                participants_list.append({
                    "user_id": str(user.id),
                    "username": user.username
                })

        # Get all messages for this conversation
        messages = db_session.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at).all()
        
        messages_emb = []
        for msg in messages:
            sender = db_session.get(User, msg.sender_id)
            if sender:
                # Check if message was read
                read_records = db_session.query(MessageRead).filter(MessageRead.message_id == msg.id).all()
                is_read = len(read_records) > 0
                
                messages_emb.append({
                    "sender_id": str(msg.sender_id),
                    "sender_username": sender.username,
                    "body": msg.body,
                    "is_read": is_read,
                    "created_at": msg.created_at.astimezone(timezone.utc) if msg.created_at else None,
                })

        doc = {
            "legacy_mysql_id": int(conv.id),
            "participants": participants_list,
            "product_id": str(conv.product_id) if conv.product_id else None,
            "messages": messages_emb,
            "message_count": len(messages_emb),
            "last_message_at": messages_emb[-1]["created_at"] if messages_emb else None,
            "created_at": conv.created_at.astimezone(timezone.utc) if conv.created_at else None,
        }

        await mongo.conversations.update_one(
            {"legacy_mysql_id": int(conv.id)},
            {"$set": doc},
            upsert=True
        )
        count += 1

    return count


async def migrate_favorites(db_session) -> int:
    """Migrate user favorites - demonstrates array of references."""
    mongo = get_mongodb()
    
    # Group favorites by user
    favorites = db_session.query(Favorite).all()
    user_favorites = {}
    
    for fav in favorites:
        if fav.user_id not in user_favorites:
            user_favorites[fav.user_id] = []
        user_favorites[fav.user_id].append({
            "product_id": str(fav.product_id),
            "created_at": fav.created_at.astimezone(timezone.utc) if fav.created_at else None
        })
    
    # Update each user's favorites array
    for user_id, favs in user_favorites.items():
        user = db_session.get(User, user_id)
        if user:
            await mongo.users.update_one(
                {"username": user.username},
                {"$set": {"favorites": favs, "favorite_count": len(favs)}}
            )
    
    return len(user_favorites)


async def migrate_to_mongodb():
    # Ensure indexes
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

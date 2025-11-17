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


async def migrate_to_mongodb():
    # Ensure indexes
    await init_mongodb()

    session = SessionLocal()
    try:
        users_count = await migrate_users(session)
        products_count = await migrate_products(session)
        print(f"MongoDB migration complete: {users_count} users, {products_count} products")
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(migrate_to_mongodb())

import random
from datetime import datetime, timedelta, timezone

from faker import Faker
import requests
from sqlalchemy.orm import Session

from app.db.mysql import SessionLocal, create_tables, drop_tables
from app.models.user import User
from app.models.location import Location
from app.models.category import Category
from app.models.product import Product
from app.models.product_details import Color, Material, Tag
from app.models.media import ProductImage
from app.models.price_history import ProductPriceHistory
from app.models.favorites import Favorite
from app.models.messages import Conversation, ConversationParticipant, Message
from app.models.sold import SoldItemArchive
from app.models.item_views import ItemView
from app.services.auth_service import AuthService

fake = Faker("en_US")

# -----------------
# DB Reset
# -----------------
def reset_db():
    drop_tables()
    create_tables()

# -----------------
# Seeders
# -----------------
def seed_locations(session: Session):
    dk_cities = [
        ("Copenhagen", "1000"),
        ("Aarhus", "8000"),
        ("Odense", "5000"),
        ("Aalborg", "9000"),
        ("Esbjerg", "6700"),
        ("Randers", "8900"),
        ("Kolding", "6000"),
        ("Horsens", "8700"),
        ("Vejle", "7100"),
        ("Roskilde", "4000"),
        ("Herning", "7400"),
        ("Silkeborg", "8600"),
        ("Helsingør", "3000"),
        ("Næstved", "4700"),
        ("Fredericia", "7000"),
        ("Viborg", "8800"),
        ("Holstebro", "7500"),
        ("Slagelse", "4200"),
        ("Hjørring", "9800"),
        ("Sønderborg", "6400"),
    ]
    locations = []
    for city, postcode in dk_cities:
        loc = Location(city=city, postcode=postcode)
        session.add(loc)
        locations.append(loc)
    session.commit()
    return locations


def seed_users(session: Session, n=150, locations=None):
    users = []
    for _ in range(n):
        first = fake.first_name()
        last = fake.last_name()
        full_name = f"{first} {last}"

        base = f"{first.lower()}.{last.lower()}"
        email = f"{base}{random.randint(1,999)}@example.com"
        username = base.replace(".", "_") + str(random.randint(1, 99))

        u = User(
            email=email,
            hashed_password=AuthService.get_password_hash("password123"),
            username=username,
            is_admin=False,
            is_active=True,
            location=random.choice(locations) if locations else None,
            full_name=full_name,
            phone=f"+45{random.randint(10000000, 99999999)}",
        )
        session.add(u)
        users.append(u)
    session.commit()
    return users


def seed_categories(session: Session):
    root = Category(name="Bicycles")
    categories = [
        Category(name="Road Bikes", parent=root),
        Category(name="Mountain Bikes", parent=root),
        Category(name="Gravel Bikes", parent=root),
        Category(name="BMX", parent=root),
        Category(name="Electric Bikes", parent=root),
        Category(name="Folding Bikes", parent=root),
        Category(name="Kids Bikes", parent=root),
    ]
    session.add(root)
    session.add_all(categories)
    session.commit()
    return [root] + categories


def seed_details(session: Session):
    colors = [Color(name=c) for c in ["Red", "Blue", "Green", "Black", "White", "Silver", "Yellow"]]
    materials = [Material(name=m) for m in ["Aluminum", "Carbon Fiber", "Steel", "Titanium"]]
    tags = [Tag(name=t) for t in [
        "Vintage", "Lightweight", "Racing", "Commuter", "Off-road", "Foldable", "E-bike"
    ]]
    session.add_all(colors + materials + tags)
    session.commit()
    return colors, materials, tags


def seed_products(session: Session, users, categories, locations, colors, materials, tags):
    brands = [
        "Trek", "Giant", "Specialized", "Cannondale", "Scott",
        "Canyon", "Bianchi", "Santa Cruz", "Merida", "Cube"
    ]
    conditions = ["new", "like_new", "good", "fair", "needs_repair"]

    products = []

    # 100 total products: 80 active, 20 sold
    for i in range(100):
        seller = random.choice(users)
        category = random.choice(categories)
        loc = random.choice(locations)

        brand = random.choice(brands)
        bike_type = category.name
        model = fake.word().capitalize()
        title = f"{brand} {model} {bike_type[:-1]}"

        # Price ranges tuned per category (raw int, then rounded)
        if bike_type == "Road Bikes":
            price = random.randint(5000, 50000)
        elif bike_type == "Mountain Bikes":
            price = random.randint(4000, 40000)
        elif bike_type == "Gravel Bikes":
            price = random.randint(6000, 35000)
        elif bike_type == "BMX":
            price = random.randint(1500, 8000)
        elif bike_type == "Electric Bikes":
            price = random.randint(8000, 60000)
        elif bike_type == "Folding Bikes":
            price = random.randint(2000, 12000)
        else:
            price = random.randint(1000, 7000)

        price = int(round(float(price) / 10.0) * 10)

        description = (
            f"This {bike_type.lower()} from {brand} is built for {random.choice(['speed', 'comfort', 'off-road adventures', 'daily commuting'])}. "
            f"Model {model} features a {random.choice(['durable', 'lightweight', 'race-ready'])} frame and {random.choice(['smooth shifting', 'powerful disc brakes', 'a comfortable geometry'])}. "
            f"{fake.paragraph(nb_sentences=2)}"
        )

        status = "active" if i < 80 else "sold"

        prod = Product(
            seller=seller,
            title=title,
            description=description,
            category=category,
            condition=random.choice(conditions),
            quantity=1,
            price_amount=price,
            price_currency="DKK",
            price_type=random.choice(["fixed", "negotiable"]),
            status=status,
            location=loc,
            created_at=fake.date_time_between(start_date="-2y", end_date="now", tzinfo=timezone.utc),
        )

        prod.colors = random.sample(colors, k=random.randint(1, 2))
        prod.materials = random.sample(materials, k=1)
        prod.tags = random.sample(tags, k=random.randint(0, 2))
        session.add(prod)
        products.append(prod)
    session.commit()

    # fetch Unsplash image
    def fetch_unsplash_bike_image(query="used_bicycle"):
        access_key = "ghdemshFN49d3S0RbExlmtShkG5MK0e9-o6fzqk1-ns"
        url = f"https://api.unsplash.com/search/photos?query={query}&per_page=30&client_id={access_key}"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data["results"]:
                    return random.choice(data["results"])["urls"]["regular"]
        except Exception:
            pass
        return "fullstack_project/frontend/public/city-bike.jpg"  # fallback local

    # add images + price history
    for p in products:
        for i in range(random.randint(1, 3)):
            keywords = f"bicycle,{p.category.name},{p.title.split()[0]}"
            img = ProductImage(
                product=p,
                url=fetch_unsplash_bike_image(keywords),
                alt_text=f"{p.title} photo",
                sort_order=i,
            )
            session.add(img)

        for j in range(random.randint(0, 3)):
            hist_amount_raw = random.uniform(float(p.price_amount) * 0.7, float(p.price_amount) * 1.3)
            hist_amount = int(round(float(hist_amount_raw) / 10.0) * 10)
            if hist_amount != int(p.price_amount):
                hist = ProductPriceHistory(
                    product=p,
                    amount=hist_amount,
                    currency="DKK",
                    changed_at=fake.date_time_between(start_date="-2y", end_date="now", tzinfo=timezone.utc),
                )
                session.add(hist)

    session.commit()
    return products


def seed_sold_archive(session: Session, products):
    sold = [p for p in products if p.status == "sold"]
    for p in sold:
        archive = SoldItemArchive(
            product_id=p.id,
            title=p.title,
            category_id=p.category_id,
            location_id=p.location_id,
            price_amount=p.price_amount,
            price_currency=p.price_currency,
            sold_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 365)),
        )
        session.add(archive)
    session.commit()


def seed_favorites(session: Session, users, products):
    for u in users:
        favs = random.sample(products, k=random.randint(0, 5))
        for p in favs:
            fav = Favorite(user=u, product=p, created_at=datetime.now(timezone.utc))
            session.add(fav)
    session.commit()


def seed_views(session: Session, users, products):
    for p in products:
        for _ in range(random.randint(0, 10)):
            viewer = random.choice(users)
            view = ItemView(
                product=p,
                viewer_user_id=viewer.id,
                viewed_at=fake.date_time_between(start_date="-2y", end_date="now", tzinfo=timezone.utc),
            )
            session.add(view)
    session.commit()


def seed_conversations(session: Session, users, products):
    for p in random.sample(products, k=10):  # conversations on ~10 products
        buyer = random.choice([u for u in users if u != p.seller])
        convo = Conversation(product_id=p.id, created_at=datetime.now(timezone.utc))
        session.add(convo)
        session.flush()  # get convo id

        participants = [p.seller, buyer]
        for u in participants:
            session.add(ConversationParticipant(conversation=convo, user=u))

        # add a few messages
        for _ in range(random.randint(2, 6)):
            sender = random.choice(participants)
            msg = Message(
                conversation_id=convo.id,
                sender_id=sender.id,
                body=fake.sentence(),
                created_at=fake.date_time_between(start_date="-1y", end_date="now", tzinfo=timezone.utc),
            )
            session.add(msg)
    session.commit()


# -----------------
# MAIN
# -----------------
def main():
    reset_db()
    db = SessionLocal()
    try:
        locations = seed_locations(db)
        users = seed_users(db, 150, locations)

        admin_user = User(
            email="admin@test.com",
            username="admin",
            full_name="Admin User",
            hashed_password=AuthService.get_password_hash("admin123"),
            is_admin=True,
            is_active=True,
            location=locations[0],
            phone="+4512345678",
        )
        db.add(admin_user)
        db.commit()
        users.append(admin_user)

        categories = seed_categories(db)
        colors, materials, tags = seed_details(db)
        products = seed_products(db, users, categories, locations, colors, materials, tags)
        seed_sold_archive(db, products)
        seed_favorites(db, users, products)
        seed_views(db, users, products)
        seed_conversations(db, users, products)

        print("✅ Users: 150 and Products: 100 (80 active, 20 sold)")
        print("✅ Admin user: admin@test.com / admin123")
    finally:
        db.close()


if __name__ == "__main__":
    main()

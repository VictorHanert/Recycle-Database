import random
from datetime import datetime, timedelta, timezone

from faker import Faker
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.mysql import SessionLocal
from app.models.user import User
from app.models.location import Location
from app.models.category import Category
from app.models.product import Product
from app.models.product_details import Color, Material, Tag
from app.models.product_images import ProductImage
from app.models.price_history import ProductPriceHistory
from app.models.favorites import Favorite
from app.models.messages import Conversation, ConversationParticipant, Message
from app.models.sold import SoldItemArchive
from app.models.item_views import ItemView
from app.services.auth_service import AuthService

fake = Faker("da_DK")
_image_cache = {}

def fetch_unsplash_bike_image(category, title=None):
    key = (category.lower(), title)
    if key in _image_cache:
        return _image_cache[key]
    access_key = "yt1xioJLpxXE3zhkoHIt4SMDifGsWTQe05sIX6ysnck" # "ghdemshFN49d3S0RbExlmtShkG5MK0e9-o6fzqk1-ns"
    style_words = ["used", "second hand", "old", "vintage", "worn", "garage", "street", "for sale"]
    category_map = {
        "city": ["city bike", "commuter bike", "urban bicycle"],
        "mountain": ["mountain bike", "mtb"],
        "road": ["road bike", "racing bicycle"],
        "kids": ["kids bike", "child bicycle"],
        "electric": ["electric bike", "ebike"],
        "bmx": ["bmx bike"],
        "hybrid": ["hybrid bicycle"],
    }
    base_terms = category_map.get(category.lower(), ["bicycle"])
    title_word = title.split()[0].lower() if title else ""
    style = random.choice(style_words)
    base_term = random.choice(base_terms)
    query = f"{style} {base_term} {title_word}".strip()
    url = f"https://api.unsplash.com/search/photos?query={query}&orientation=landscape&per_page=30&content_filter=low&client_id={access_key}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data["results"]:
                img_url = random.choice(data["results"])["urls"]["regular"]
                _image_cache[key] = img_url
                return img_url
    except Exception:
        pass
    fallbacks = ["/images/city-bike.jpg", "/images/mountain-bike.jpg", "/images/racing-bike.jpg"]
    img_url = random.choice(fallbacks)
    _image_cache[key] = img_url
    return img_url

def seed_locations(session: Session):
    dk_cities = [
        ("Copenhagen", "1000"),
        ("Hellerup", "2900"),
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
        ("Hillerød", "3400"),
        ("Fredensborg", "3480"),
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

        email_patterns = [
            f"{first.lower()}.{last.lower()}{random.randint(1,999)}@gmail.com",
            f"{first.lower()}{last.lower()}{random.randint(1,99)}@hotmail.com",
            f"{first.lower()}_{last.lower()}{random.randint(1,999)}@yahoo.com",
            f"{first.lower()}{random.randint(10,99)}@example.com",
        ]
        email = random.choice(email_patterns)

        username_patterns = [
            f"{first.lower()}_{last.lower()}{random.randint(1,99)}",
            f"{first.lower()}{last.lower()}{random.randint(1,999)}",
            f"{first[0].lower()}{last.lower()}{random.randint(1,99)}",
            f"{first.lower()}{random.randint(10,99)}",
        ]
        username = random.choice(username_patterns)

        phone_patterns = [
            f"{random.randint(10000000, 99999999)}",
            f"+45{random.randint(10000000, 99999999)}",
        ]
        phone = random.choice(phone_patterns)

        u = User(
            email=email,
            hashed_password=AuthService.get_password_hash("password123"),
            username=username,
            is_admin=False,
            is_active=True,
            location=random.choice(locations) if locations else None,
            full_name=full_name,
            phone=phone,
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
    brand_models = {
        "Trek": ["Domane", "Madone", "Emonda", "Fuel", "Slash", "Powerfly"],
        "Giant": ["TCR", "Defy", "Contend", "Trance", "Reign", "Stance"],
        "Specialized": ["Tarmac", "Venge", "Roubaix", "Allez", "Stumpjumper", "Epic"],
        "Cannondale": ["SuperSix", "Synapse", "Topstone", "Scalpel", "Habit", "Jekyll"],
        "Scott": ["Addict", "Speedster", "Foil", "Spark", "Genius", "Ransom"],
        "Canyon": ["Aeroad", "Endurace", "Grail", "Spectral", "Neuron", "Lux"],
        "Bianchi": ["Oltre", "Specialissima", "Intenso", "Methanol", "Impulso"],
        "Santa Cruz": ["Vader", "Hightower", "Nomad", "Megatower", "Tallboy"],
        "Merida": ["Scultura", "Reacto", "Silex", "Big.Nine", "Big.Seven"],
        "Cube": ["Aero", "Racing", "Cross", "Reaction", "Stereo", "Nuroad"]
    }

    conditions = ["new", "like_new", "good", "fair", "needs_repair"]
    condition_weights = [0.1, 0.3, 0.4, 0.15, 0.05]

    products = []

    for i in range(100):
        seller = random.choice(users)

        if random.random() < 0.15:
            category = categories[0]
        else:
            category = random.choice(categories[1:])

        loc = random.choice(locations)

        brand = random.choice(list(brand_models.keys()))
        bike_type = category.name

        if brand in brand_models:
            model = random.choice(brand_models[brand])
        else:
            model = fake.word().capitalize()

        title_patterns = [
            f"{brand} {model} {bike_type[:-1]}",
            f"{brand} {model}",
            f"{bike_type[:-1]} {brand} {model}",
            f"Used {brand} {model}",
        ]
        title = random.choice(title_patterns)

        # price ranges with realistic variations
        base_prices = {
            "Bicycles": (2000, 8000),
            "Road Bikes": (8000, 45000),
            "Mountain Bikes": (6000, 35000),
            "Gravel Bikes": (10000, 40000),
            "BMX": (2000, 8000),
            "Electric Bikes": (5000, 30000),
            "Folding Bikes": (3000, 9000),
            "Kids Bikes": (250, 5000),
        }

        min_price, max_price = base_prices.get(bike_type, (2000, 20000))
        price = random.randint(min_price, max_price)
        price = int(round(float(price) / 10.0) * 10)

        features = [
            "carbon frame", "aluminum frame", "disc brakes", "rim brakes",
            "electronic shifting", "mechanical shifting", "carbon wheels",
            "integrated cockpit", "drop handlebars", "flat handlebars", "new brakes"
        ]

        purposes = [
            "daily commuting", "road racing", "mountain biking", "gravel riding",
            "urban cycling", "touring", "trail riding", "enduro riding"
        ]

        description_templates = [
            f"Excellent {bike_type.lower()} from {brand}. This {model} features a {random.choice(['lightweight', 'durable', 'high-performance'])} {random.choice(features)} and is perfect for {random.choice(purposes)}. {fake.paragraph(nb_sentences=2)}",
            f"Well-maintained {brand} {model} {bike_type.lower()}. Great for {random.choice(purposes)} with {random.choice(features)}. {fake.paragraph(nb_sentences=2)}",
            f"High-quality {bike_type.lower()} by {brand}. The {model} model offers {random.choice(features)} and excellent {random.choice(['handling', 'comfort', 'speed', 'durability'])}. {fake.paragraph(nb_sentences=2)}",
        ]

        description = random.choice(description_templates)
        condition = random.choices(conditions, weights=condition_weights)[0]

        # Some products have quantity > 1 (bulk sellers)
        quantity = 1 if random.random() < 0.85 else random.randint(2, 5)

        # Price type based on condition and category
        if condition == "new":
            price_type = random.choice(["fixed", "negotiable"])
        else:
            price_type = random.choices(["fixed", "negotiable"], weights=[0.7, 0.3])[0]

        status = "active" if i < 80 else "sold"

        days_old_weights = [0.1, 0.15, 0.2, 0.25, 0.3]
        days_old = random.choices([30, 90, 180, 270, 365*2], weights=days_old_weights)[0]
        created_at = datetime.now(timezone.utc) - timedelta(days=random.randint(1, days_old))

        prod = Product(
            seller=seller,
            title=title,
            description=description,
            category=category,
            condition=condition,
            quantity=quantity,
            price_amount=price,
            price_currency="DKK",
            price_type=price_type,
            status=status,
            location=loc,
            created_at=created_at,
        )

        prod.colors = random.sample(colors, k=random.choices([1, 2, 3], weights=[0.5, 0.3, 0.2])[0])
        prod.materials = random.sample(materials, k=1)
        prod.tags = random.sample(tags, k=random.choices([0, 1, 2], weights=[0.2, 0.5, 0.3])[0])
        session.add(prod)
        products.append(prod)
    session.commit()
        
    # add images + price history
    for p in products:
        for i in range(random.randint(1, 3)):
            keywords = f"bicycle,{p.category.name},{p.title.split()[0]}"
            img = ProductImage(
                product=p,
                url=fetch_unsplash_bike_image(category=p.category.name, title=p.title),
                alt_text=f"{p.title} photo",
                sort_order=i,
            )
            session.add(img)

        # Generate price history with unique timestamps
        num_changes = random.randint(0, 4)
        if num_changes > 0:
            # Ensure both datetimes are timezone-aware
            now_utc = datetime.now(timezone.utc)
            created_at_utc = p.created_at.replace(tzinfo=timezone.utc) if p.created_at.tzinfo is None else p.created_at
            days_since_creation = max(1, (now_utc - created_at_utc).days)

            # Generate unique days_before values
            available_days = list(range(1, days_since_creation + 1))
            selected_days = random.sample(available_days, min(num_changes, len(available_days)))

            for days_before in selected_days:
                if random.random() < 0.7:  # 70% chance of price decrease
                    change_factor = random.uniform(0.65, 0.97)  # -15% to -3%
                else:
                    change_factor = random.uniform(0.7, 1.05)  # -30% to +5%

                hist_amount_raw = float(p.price_amount) * change_factor
                hist_amount = int(round(hist_amount_raw / 10.0) * 10)

                if hist_amount != int(p.price_amount):
                    changed_at = created_at_utc - timedelta(days=days_before)
                    hist = ProductPriceHistory(
                        product=p,
                        amount=hist_amount,
                        currency="DKK",
                        changed_at=changed_at,
                    )
                    session.add(hist)

    session.commit()
    return products


def seed_sold_archive(session: Session, products):
    sold = [p for p in products if p.status == "sold"]
    for p in sold:
        days_ago_weights = [0.4, 0.3, 0.2, 0.07, 0.03]  # Favor recent sales
        days_ago = random.choices([7, 30, 90, 180, 365], weights=days_ago_weights)[0]
        sold_at = datetime.now(timezone.utc) - timedelta(days=random.randint(1, days_ago))

        archive = SoldItemArchive(
            product_id=p.id,
            title=p.title,
            category_id=p.category_id,
            location_id=p.location_id,
            price_amount=p.price_amount,
            price_currency=p.price_currency,
            sold_at=sold_at,
        )
        session.add(archive)
    session.commit()


def seed_favorites(session: Session, users, products):
    for u in users:
        other_products = [p for p in products if p.seller_id != u.id]
        if other_products:
            num_favs = random.choices([0, 1, 2, 3, 4, 5], weights=[0.2, 0.2, 0.25, 0.2, 0.1, 0.05])[0]
            favs = random.sample(other_products, k=min(num_favs, len(other_products)))
            for p in favs:
                # Ensure both datetimes are timezone-aware
                now_utc = datetime.now(timezone.utc)
                created_at_utc = p.created_at.replace(tzinfo=timezone.utc) if p.created_at.tzinfo is None else p.created_at
                days_since_creation = max(0, (now_utc - created_at_utc).days)
                days_after = random.randint(0, days_since_creation)
                fav_date = created_at_utc + timedelta(days=days_after)
                fav = Favorite(user=u, product=p, created_at=fav_date)
                session.add(fav)
    session.commit()


def seed_views(session: Session, users, products):
    for p in products:
        potential_viewers = [u for u in users if u.id != p.seller_id and u.is_active]
        if potential_viewers:
            # Ensure both datetimes are timezone-aware for comparison
            created_at_utc = p.created_at.replace(tzinfo=timezone.utc) if p.created_at.tzinfo is None else p.created_at
            base_views = 2 if created_at_utc > datetime.now(timezone.utc) - timedelta(days=30) else 1
            max_views = 15
            view_range = list(range(base_views, max_views))
            # Create weights that match the range length
            num_options = len(view_range)
            if num_options <= 5:
                weights = [1.0 / num_options] * num_options
            else:
                # Favor lower numbers: decreasing weights
                weights = [0.3, 0.25, 0.2, 0.15, 0.1] + [0.05] * (num_options - 5)
            view_count = random.choices(view_range, weights=weights)[0]

            for _ in range(view_count):
                viewer = random.choice(potential_viewers)
                # Ensure both datetimes are timezone-aware
                now_utc = datetime.now(timezone.utc)
                days_since_creation = max(0, (now_utc - created_at_utc).days)
                days_after = random.randint(0, days_since_creation)
                view_date = created_at_utc + timedelta(days=days_after)

                view = ItemView(
                    product=p,
                    viewer_user_id=viewer.id,
                    viewed_at=view_date,
                )
                session.add(view)
    session.commit()


def seed_conversations(session: Session, users, products):
    active_products = [p for p in products if p.status == "active"]
    conversation_count = min(len(active_products) // 8, 25)  # ~12% of products have conversations

    for p in random.sample(active_products, k=conversation_count):
        buyer = random.choice([u for u in users if u.id != p.seller_id and u.is_active])

        # Conversation should start after product creation
        # Ensure both datetimes are timezone-aware
        now_utc = datetime.now(timezone.utc)
        created_at_utc = p.created_at.replace(tzinfo=timezone.utc) if p.created_at.tzinfo is None else p.created_at
        days_since_creation = max(0, (now_utc - created_at_utc).days)
        days_after = random.randint(0, days_since_creation)
        convo_start = created_at_utc + timedelta(days=days_after)

        convo = Conversation(product_id=p.id, created_at=convo_start)
        session.add(convo)
        session.flush()

        participants = [p.seller, buyer]
        for u in participants:
            session.add(ConversationParticipant(conversation=convo, user=u))

        # Realistic message patterns for seeding
        message_templates = [
            "Hi! I'm interested in your {product}. Is it still available?",
            "Hello! Is the {product} still for sale?",
            "Hi there! Can you tell me more about the {product}?",
            "Hello! What's the condition of the {product}?",
            "Hi! Is the price negotiable for the {product}?",
            "Hello! Do you have photos of the {product}?",
            "Hi! Can I come see the {product}?",
            "Hello! Is the {product} in {location}?",
            "Hi! How old is the {product}?",
            "Hello! What size is the {product}?",
            "Hi! Does the {product} come with accessories?",
            "Hello! Can you deliver the {product}?",
            "Hi! What's your best price for the {product}?",
            "Hello! Is the {product} still available? I saw it on the site.",
            "Hi! Can we meet to see the {product}?",
        ]

        response_templates = [
            "Hi! Yes, it's still available. What would you like to know?",
            "Hello! Yes, the {product} is still for sale.",
            "Hi there! The {product} is in {condition} condition.",
            "Hello! The price is {price} DKK{fixed}.",
            "Hi! Yes, I can show you more photos.",
            "Hello! We can meet in {location} to see it.",
            "Hi! The {product} is about {age} old.",
            "Hello! It's a {size} size.",
            "Hi! It comes with {accessories}.",
            "Hello! I can deliver for an extra fee.",
            "Hi! My best price is {best_price} DKK.",
            "Hello! Yes, let's arrange a viewing!",
        ]

        # Generate conversation with 2-8 messages
        message_count = random.randint(2, 8)
        current_time = convo_start

        for i in range(message_count):
            sender = participants[i % 2]  # Alternate between buyer and seller
            time_gap = timedelta(minutes=random.randint(30, 4*60))  # 30min to 4 hours between messages
            current_time += time_gap

            if i == 0:
                # First message from buyer
                body = random.choice(message_templates).format(
                    product=p.title.split()[1] if len(p.title.split()) > 1 else p.title,
                    location=p.location.city,
                )
            else:
                # Responses
                body = random.choice(response_templates).format(
                    product=p.title.split()[1] if len(p.title.split()) > 1 else p.title,
                    condition=p.condition.replace('_', ' '),
                    price=p.price_amount,
                    fixed=" (fixed price)" if p.price_type == "fixed" else " (negotiable)",
                    location=p.location.city,
                    age=f"{random.randint(1, 5)} years",
                    size=random.choice(["S", "M", "L", "XL"]),
                    accessories=random.choice(["original pedals", "lights", "lock", "pump", "tires and brakes"]),
                    best_price=int(float(p.price_amount) * random.uniform(0.85, 0.95))
                )

            msg = Message(
                conversation_id=convo.id,
                sender_id=sender.id,
                body=body,
                created_at=current_time,
            )
            session.add(msg)
    session.commit()


def main():
    print("🚀 Starting database seeding with realistic data...")

    db = SessionLocal()
    try:
        # Check if database already has data
        user_count = db.query(User).count()
        product_count = db.query(Product).count()

        if user_count > 0 or product_count > 0:
            print("⚠️  WARNING: Database already contains data!")
            print(f"   - {user_count} users")
            print(f"   - {product_count} products")
            print()
            print("Running seed.py will DELETE ALL EXISTING DATA and create fresh test data.")
            print()
            response = input("Are you sure you want to continue? (y/N): ").strip().lower()

            if response not in ['y', 'yes']:
                print("Seeding cancelled.")
                return

            print("🗑️  Clearing existing data...")

            # Use TRUNCATE which is faster and resets auto-increment counters
            try:
                db.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                db.execute(text("TRUNCATE TABLE messages"))
                db.execute(text("TRUNCATE TABLE conversation_participants"))
                db.execute(text("TRUNCATE TABLE conversations"))
                db.execute(text("TRUNCATE TABLE item_views"))
                db.execute(text("TRUNCATE TABLE favorites"))
                db.execute(text("TRUNCATE TABLE sold_item_archive"))
                db.execute(text("TRUNCATE TABLE product_price_history"))
                db.execute(text("TRUNCATE TABLE product_images"))
                db.execute(text("TRUNCATE TABLE product_colors"))
                db.execute(text("TRUNCATE TABLE product_materials"))
                db.execute(text("TRUNCATE TABLE product_tags"))
                db.execute(text("TRUNCATE TABLE products"))
                db.execute(text("TRUNCATE TABLE users"))
                db.execute(text("TRUNCATE TABLE categories"))
                db.execute(text("TRUNCATE TABLE colors"))
                db.execute(text("TRUNCATE TABLE materials"))
                db.execute(text("TRUNCATE TABLE tags"))
                db.execute(text("TRUNCATE TABLE locations"))
                db.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                db.commit()
                print("✅ Database cleared.")
                # Create a fresh session to avoid any caching issues
                db.close()
                db = SessionLocal()
            except Exception as e:
                db.rollback()
                print(f"Error during clearing: {e}")
                # Fallback to individual deletes
                db.execute(text("DELETE FROM messages"))
                db.execute(text("DELETE FROM conversation_participants"))
                db.execute(text("DELETE FROM conversations"))
                db.execute(text("DELETE FROM item_views"))
                db.execute(text("DELETE FROM favorites"))
                db.execute(text("DELETE FROM sold_item_archive"))
                db.execute(text("DELETE FROM product_price_history"))
                db.execute(text("DELETE FROM product_images"))
                db.execute(text("DELETE FROM product_colors"))
                db.execute(text("DELETE FROM product_materials"))
                db.execute(text("DELETE FROM product_tags"))
                db.execute(text("DELETE FROM products"))
                db.execute(text("DELETE FROM users"))
                # Delete child categories first, then parent categories
                db.execute(text("DELETE FROM categories WHERE parent_id IS NOT NULL"))
                db.execute(text("DELETE FROM categories WHERE parent_id IS NULL"))
                db.execute(text("DELETE FROM colors"))
                db.execute(text("DELETE FROM materials"))
                db.execute(text("DELETE FROM tags"))
                db.execute(text("DELETE FROM locations"))
                db.commit()
                print("✅ Database cleared (fallback method).")

        locations = seed_locations(db)
        users = seed_users(db, 85, locations)
        print(f"Seeded {len(users)} users")

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
        non_admin_users = [u for u in users if not u.is_admin]
        products = seed_products(db, non_admin_users, categories, locations, colors, materials, tags)
        print(f"Seeded {len(products)} products ({sum(1 for p in products if p.status == 'active')} active, {sum(1 for p in products if p.status == 'sold')} sold)")

        seed_sold_archive(db, products)
        seed_favorites(db, users, products)
        seed_views(db, users, products)
        seed_conversations(db, users, products)

        print("✅ Created admin user: admin@test.com / admin123")

    finally:
        db.close()


if __name__ == "__main__":
    main()

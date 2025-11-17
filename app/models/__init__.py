"""Models package initialization."""

# Import all models to ensure they are registered with SQLAlchemy
from app.models.user import User
from app.models.location import Location
from app.models.category import Category
from app.models.product import Product
from app.models.product_images import ProductImage
from app.models.favorites import Favorite
from app.models.item_views import ItemView
from app.models.price_history import ProductPriceHistory
from app.models.sold import SoldItemArchive
from app.models.messages import Conversation, ConversationParticipant, Message, MessageRead
from app.models.product_details import Color, Material, Tag, ProductColor, ProductMaterial, ProductTag

__all__ = [
    "User",
    "Location", 
    "Category",
    "Product",
    "ProductImage",
    "Favorite",
    "ItemView", 
    "ProductPriceHistory",
    "SoldItemArchive",
    "Conversation",
    "ConversationParticipant", 
    "Message",
    "MessageRead",
    "Color",
    "Material", 
    "Tag",
    "ProductColor",
    "ProductMaterial",
    "ProductTag"
]

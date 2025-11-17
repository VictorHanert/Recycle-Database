"""Configuration settings for the application."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Database
    database_url: str = "mysql+pymysql://root:root@localhost:3307/marketplace"

    # JWT
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Environment
    environment: str = "development"
    debug: bool = False

    # Server Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # MongoDB Configuration (optional)
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "marketplace"

    # Neo4j Configuration (optional)
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Azure Storage Configuration
    azure_storage_connection_string: str = ""
    storage_mode: str = "local"  # "local" or "azure"

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

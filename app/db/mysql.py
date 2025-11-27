import logging
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    echo=False,  # SQL query logging
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=300,  # Recycle connections after 5 minutes
    pool_size=5,  # Connection pool size
    max_overflow=10,  # Max connections beyond pool_size
    connect_args={
        'connect_timeout': 10,  # Connection timeout in seconds
    }
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create declarative base class
class Base(DeclarativeBase):
    pass


# Dependency to get database session
def get_db():
    """Database dependency for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create all tables
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """Drop all database tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)


# Database initialization functions
def run_migrations():
    """Run Alembic migrations to update database schema."""
    try:
        logger.info("Running database migrations...")
        subprocess.run(["alembic", "upgrade", "head"], check=True, capture_output=True)
        logger.info("Migrations completed")
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed: {e.stderr.decode()}")
        raise
    except FileNotFoundError:
        logger.warning("Alembic not found, skipping migrations")


def init_stored_objects():
    """Initialize stored procedures, functions, views, and triggers from SQL file."""
    sql_file = Path(__file__).parent.parent.parent / "scripts" / "mysql" / "init_database.sql"
    
    if not sql_file.exists():
        logger.warning("init_database.sql not found, skipping")
        return
    
    logger.info("Initializing database objects...")
    db = SessionLocal()
    
    try:
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        cursor = db.connection().connection.cursor()
        
        # Parse SQL handling DELIMITER changes
        current_delimiter = ';'
        statements = []
        current_statement = []
        
        for line in sql_content.split('\n'):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('--'):
                continue
                
            # Handle DELIMITER command
            if line.upper().startswith('DELIMITER'):
                if current_statement:
                    statements.append('\n'.join(current_statement))
                    current_statement = []
                current_delimiter = line.split(None, 1)[1] if len(line.split()) > 1 else ';'
                continue
            
            current_statement.append(line)
            
            # Check if statement is complete
            if line.endswith(current_delimiter):
                current_statement[-1] = current_statement[-1][:-len(current_delimiter)].strip()
                if current_statement[-1]:
                    statements.append('\n'.join(current_statement))
                elif len(current_statement) > 1:
                    statements.append('\n'.join(current_statement[:-1]))
                current_statement = []
        
        # Execute each statement
        for statement in statements:
            statement = statement.strip()
            if statement:
                try:
                    cursor.execute(statement)
                except Exception as e:
                    error_msg = str(e).lower()
                    if "already exists" not in error_msg and "duplicate" not in error_msg:
                        logger.warning(f"SQL note: {e}")
        
        db.connection().commit()
        logger.info("Database objects initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database objects: {e}")
        db.connection().rollback()
        raise
    finally:
        db.close()


def seed_database():
    """Seed database with test data if not already done."""
    try:
        logger.info("Checking if database needs seeding...")
        
        # Check if admin user exists
        db = SessionLocal()
        from app.models.user import User
        admin_exists = db.query(User).filter(User.email == "admin@test.com").first()
        db.close()
        
        if admin_exists:
            logger.info("Database already seeded, skipping")
            return
        
        logger.info("Seeding database with test data...")
        result = subprocess.run(
            [sys.executable, "-m", "scripts.seed"], 
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            logger.info("Database seeding completed")
        else:
            logger.error(f"Database seeding failed: {result.stderr}")
            raise Exception(f"Seeding failed: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Failed to seed database: {e}")
        raise


def initialize_database():
    """Initialize database: run migrations, create objects, and seed data."""
    logger.info("Starting database initialization...")
    run_migrations()
    init_stored_objects()
    seed_database()
    logger.info("Database initialization completed")
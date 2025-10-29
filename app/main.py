import logging
import time
import subprocess
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routers import auth, products, admin, profile, location
from app.db.mysql import SessionLocal
from app.config import get_settings
from app.middleware import (
    create_error_response,
    log_http_exception,
    log_validation_exception,
    log_general_exception,
    format_validation_errors
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


def run_migrations():
    """Run Alembic migrations to ensure database schema is current."""
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
    """Initialize stored procedures, functions, views, triggers, and events."""
    sql_file = Path(__file__).parent.parent / "scripts" / "mysql" / "init_database.sql"
    
    if not sql_file.exists():
        logger.warning("init_database.sql not found, skipping")
        return
    
    logger.info("Initializing database objects...")
    db = SessionLocal()
    
    try:
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        cursor = db.connection().connection.cursor()
        
        for statement in sql_content.split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    cursor.execute(statement)
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.debug(f"SQL note: {e}")
        
        db.connection().commit()
        logger.info("Database objects initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database objects: {e}")
        raise
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting application...")
    run_migrations()
    init_stored_objects()
    logger.info("Application ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")

app = FastAPI(
    title="Marketplace API",
    description="A modern marketplace platform where users can list and sell products",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
cors_origins = settings.cors_origins.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log HTTP responses with timing"""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"⬅️  {response.status_code} {request.method} {request.url.path} ({duration:.3f}s)")
    
    return response

# Custom exception handlers with logging
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    """Handle HTTP exceptions with logging"""
    log_http_exception(exc, str(request.url.path))
    return create_error_response(exc.status_code, exc.detail, str(request.url.path))

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request, exc):
    """Handle validation errors with logging"""
    log_validation_exception(exc, str(request.url.path))
    errors = format_validation_errors(exc)
    return create_error_response(422, "Validation error", str(request.url.path), errors)

@app.exception_handler(Exception)
async def custom_general_exception_handler(request, exc):
    """Handle unexpected exceptions with logging"""
    log_general_exception(exc, str(request.url.path))
    return create_error_response(500, "Internal server error", str(request.url.path))

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])
app.include_router(location.router, prefix="/api/locations", tags=["Locations"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Marketplace API is running!",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Detailed health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "message": "Marketplace API is running!",
        "databases": {
            "mysql_configured": bool(settings.database_url)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)

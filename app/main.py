import logging
import sentry_sdk
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.routers import activity_router, admin_router, auth_router, favorites_router, location_router, products_router, profile_router, messages_router
from app.routers.mongodb import users as mongodb_users_router, products as mongodb_products_router
from app.routers.neo4j import users as neo4j_users_router, products as neo4j_products_router
from app.config import get_settings
from app.db.mysql import initialize_database
from app.db.mongodb import init_mongodb, close_mongodb
from app.db.neo4j import init_neo4j, close_neo4j
from app.middleware import (
    create_error_response,
    log_http_exception,
    log_validation_exception,
    log_general_exception,
    format_validation_errors
)

from typing import Union, Awaitable
from starlette.responses import Response

HandlerReturn = Union[Response, Awaitable[Response]]

def rate_limit_handler(request: Request, exc: Exception) -> HandlerReturn:
    assert isinstance(exc, RateLimitExceeded)
    return _rate_limit_exceeded_handler(request, exc)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100% of sampled transactions.
    profiles_sample_rate=1.0,
    send_default_pii=True,
)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting application...")
    initialize_database()
    logger.info("Application ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await close_mongodb()
    await close_neo4j()

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

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

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

# MySQL routers
app.include_router(auth_router.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(products_router.router, prefix="/api/products", tags=["Products"])
app.include_router(favorites_router.router, prefix="/api/favorites", tags=["Favorites"])
app.include_router(activity_router.router, prefix="/api/activity", tags=["Activity & History"])
app.include_router(admin_router.router, prefix="/api/admin", tags=["Admin"])
app.include_router(profile_router.router, prefix="/api/profile", tags=["Profile"])
app.include_router(messages_router.router, prefix="/api/messages", tags=["Messages"])
app.include_router(location_router.router, prefix="/api/locations", tags=["Locations"])

# MongoDB routers
app.include_router(mongodb_users_router.router, prefix="/mongodb/users", tags=["MongoDB Users"])
app.include_router(mongodb_products_router.router, prefix="/mongodb/products", tags=["MongoDB Products"])

# Neo4j routers
app.include_router(neo4j_users_router.router, prefix="/neo4j/users", tags=["Neo4j Users"])
app.include_router(neo4j_products_router.router, prefix="/neo4j/products", tags=["Neo4j Products"])


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
            "mysql_configured": bool(settings.database_url),
            "mongodb_configured": bool(settings.mongodb_url),
            "neo4j_configured": bool(settings.neo4j_url)
        }
    }

@app.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1 / 0
    return {"result": division_by_zero}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)

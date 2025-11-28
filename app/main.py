import logging
import time
from contextlib import asynccontextmanager
from typing import Union, Awaitable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.routers.mongodb import users as mongodb_users_router
from app.routers.mongodb import products as mongodb_products_router
from app.routers.mongodb import auth as mongodb_auth_router

from app.routers.neo4j import users as neo4j_users_router
from app.routers.neo4j import products as neo4j_products_router
from app.routers.neo4j import auth as neo4j_auth_router

from app.config import get_settings
from app.db.mongodb import init_mongodb, close_mongodb
from app.db.neo4j import init_neo4j, close_neo4j
from app.middleware import (
    create_error_response,
    log_http_exception,
    log_validation_exception,
    log_general_exception,
    format_validation_errors
)


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

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    logger.info("Starting application...")

    # Ensure MongoDB and Neo4j indexes/constraints are created
    try:
        await init_mongodb()
    except Exception as exc:
        logger.warning(f"MongoDB init warning: {exc}")
    try:
        await init_neo4j()
    except Exception as exc:
        logger.warning(f"Neo4j init warning: {exc}")
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


# MongoDB routers
app.include_router(mongodb_auth_router.router, prefix="/mongodb/auth", tags=["MongoDB Auth"])
app.include_router(mongodb_users_router.router, prefix="/mongodb/users", tags=["MongoDB Users"])
app.include_router(mongodb_products_router.router, prefix="/mongodb/products", tags=["MongoDB Products"])

# Neo4j routers
app.include_router(neo4j_auth_router.router, prefix="/neo4j/auth", tags=["Neo4j Auth"])
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
            "mongodb_configured": bool(settings.mongodb_url),
            "neo4j_configured": bool(settings.neo4j_url)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)

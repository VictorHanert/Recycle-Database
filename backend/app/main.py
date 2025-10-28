import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routers import auth, products, admin, profile, location
from app.db.mysql import create_tables
from app.config import get_settings
from app.middleware import (
    create_error_response,
    log_http_exception,
    log_validation_exception,
    log_general_exception,
    format_validation_errors
)

# Simple logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Log startup
logger.info("-=- Starting Marketplace API -=-")

# Create database tables on startup
create_tables()
logger.info("-=- Database initialized -=-")

app = FastAPI(
    title="Marketplace API",
    description="A modern marketplace platform where users can list and sell products",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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

# Request/Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses with timing"""
    start_time = time.time()
    
    # Log request
    logger.info(f"➡️  {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Log response with timing
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

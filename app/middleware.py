from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_error_response(status_code: int, message: str, path: str, details=None):
    """Helper function to create consistent error responses"""
    content = {
        "error": True,
        "message": message,
        "status_code": status_code,
        "path": path
    }
    if details:
        content["details"] = details
    return JSONResponse(status_code=status_code, content=content)


def log_http_exception(exc: StarletteHTTPException, path: str):
    """Log HTTP exceptions"""
    logger.warning(f"HTTP Exception: {exc.detail} - Path: {path}")


def log_validation_exception(exc: RequestValidationError, path: str):
    """Log validation exceptions"""
    logger.warning(f"Validation Error: {exc} - Path: {path}")


def log_general_exception(exc: Exception, path: str):
    """Log general exceptions with full stack trace"""
    logger.exception(f"Unexpected error on {path}: {exc}")


def format_validation_errors(exc: RequestValidationError):
    """Format validation errors for response"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    return errors

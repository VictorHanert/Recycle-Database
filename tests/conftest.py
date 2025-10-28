"""Test configuration and fixtures"""
import pytest


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "SecurePass123!",
        "full_name": "Test User"
    }


@pytest.fixture
def sample_product_data():
    """Sample product data for testing"""
    return {
        "title": "Test Product",
        "description": "A test product description",
        "price": 99.99,
        "category_id": 1,
        "location_id": 1
    }

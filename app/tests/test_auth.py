import pytest
from fastapi.testclient import TestClient

from app.core.security import verify_password


def test_student_register(client: TestClient):
    """Test student registration."""
    response = client.post(
        "/api/v1/auth/student/register",
        json={
            "name": "Test Student",
            "email": "test@example.com",
            "phone": "1234567890",
            "password": "testpassword123",
            "password_confirm": "testpassword123",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert "refresh_token" in data


def test_student_login(client: TestClient):
    """Test student login."""
    # First register a student
    client.post(
        "/api/v1/auth/student/register",
        json={
            "name": "Login Test",
            "email": "login@example.com", 
            "phone": "0987654321",
            "password": "loginpass123",
            "password_confirm": "loginpass123",
        }
    )
    
    # Then try to login
    response = client.post(
        "/api/v1/auth/student/login",
        json={
            "email": "login@example.com",
            "password": "loginpass123",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert "refresh_token" in data


def test_student_login_invalid_credentials(client: TestClient):
    """Test student login with invalid credentials."""
    response = client.post(
        "/api/v1/auth/student/login",
        json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword",
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect email or password"


def test_student_register_duplicate_email(client: TestClient):
    """Test registration with duplicate email."""
    # Register first student
    client.post(
        "/api/v1/auth/student/register",
        json={
            "name": "First Student",
            "email": "duplicate@example.com",
            "phone": "1111111111",
            "password": "password123",
            "password_confirm": "password123",
        }
    )
    
    # Try to register with same email
    response = client.post(
        "/api/v1/auth/student/register",
        json={
            "name": "Second Student", 
            "email": "duplicate@example.com",
            "phone": "2222222222",
            "password": "password456",
            "password_confirm": "password456",
        }
    )
    assert response.status_code == 400
    assert "email already exists" in response.json()["detail"] 
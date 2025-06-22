import pytest
from fastapi.testclient import TestClient

from app.core.security import verify_password


def test_student_register(client: TestClient):
    """Test student registration."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "fname": "Test",
            "lname": "Student",
            "email": "test@example.com",
            "phone_number": "1234567890",
            "password": "testpassword123",
            "password_confirm": "testpassword123",
            "user_type": "student"
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
        "/api/v1/auth/register",
        json={
            "fname": "Login",
            "lname": "Test",
            "email": "login@example.com", 
            "phone_number": "0987654321",
            "password": "loginpass123",
            "password_confirm": "loginpass123",
            "user_type": "student"
        }
    )
    
    # Then try to login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "loginpass123",
            "user_type": "student"
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
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword",
            "user_type": "student"
        }
    )
    assert response.status_code == 404
    assert "user_not_found" in response.json()["detail"]["error"]


def test_student_register_duplicate_email(client: TestClient):
    """Test registration with duplicate email."""
    # Register first student
    client.post(
        "/api/v1/auth/register",
        json={
            "fname": "First",
            "lname": "Student",
            "email": "duplicate@example.com",
            "phone_number": "1111111111",
            "password": "password123",
            "password_confirm": "password123",
            "user_type": "student"
        }
    )
    
    # Try to register with same email
    response = client.post(
        "/api/v1/auth/register",
        json={
            "fname": "Second",
            "lname": "Student", 
            "email": "duplicate@example.com",
            "phone_number": "2222222222",
            "password": "password456",
            "password_confirm": "password456",
            "user_type": "student"
        }
    )
    assert response.status_code == 409
    assert "already_exists" in response.json()["detail"]["error"] 
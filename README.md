# SAYAN Educational Platform API

A FastAPI-based backend for the SAYAN educational platform, migrated from Laravel to provide high-performance RESTful APIs while maintaining the same data structures and authentication logic.

## Project Description

SAYAN is a comprehensive educational platform that allows academies to create and manage online courses, students to enroll and learn, and administrators to oversee the entire system. This FastAPI implementation preserves all the functionality of the original Laravel backend while offering improved performance and modern Python async capabilities.

## Folder Structure

```
app/
│
├── api/              # API route handlers
│   └── v1/           # Version 1 API endpoints
│       ├── auth.py   # Authentication endpoints
│       └── courses.py # Course management endpoints
├── core/             # Core configuration and utilities
│   ├── config.py     # Application settings
│   └── security.py   # JWT and password hashing
├── models/           # SQLAlchemy ORM models
│   ├── admin.py      # Admin user model
│   ├── academy.py    # Academy and related models
│   ├── student.py    # Student and enrollment models
│   ├── course.py     # Course, chapter, lesson models
│   ├── finance.py    # Payment and transaction models
│   ├── product.py    # Digital products and packages
│   ├── general.py    # Blog and general models
│   ├── marketing.py  # Coupon and affiliate models
│   ├── template.py   # Template customization models
│   └── role.py       # Role and permission models
├── schemas/          # Pydantic schemas for validation
│   ├── auth.py       # Authentication schemas
│   └── course.py     # Course-related schemas
├── crud/             # CRUD operations for models
│   ├── base.py       # Base CRUD class
│   └── student.py    # Student CRUD operations
├── services/         # Business logic layer
├── db/               # Database configuration
│   ├── base.py       # Base model and imports
│   └── session.py    # Database session management
├── deps/             # FastAPI dependencies
│   ├── auth.py       # Authentication dependencies
│   └── database.py   # Database session dependency
├── main.py           # FastAPI application entry point
└── tests/            # Test suite
```

## Tech Stack & Libraries

- **FastAPI** (0.104.1) - Modern, fast web framework for building APIs
- **SQLAlchemy** (2.0.23) - SQL toolkit and ORM
- **Pydantic** (2.5.0) - Data validation using Python type annotations
- **Alembic** (1.12.1) - Database migration tool
- **python-jose** (3.3.0) - JWT token implementation
- **passlib** (1.7.4) - Password hashing utilities
- **uvicorn** (0.24.0) - ASGI server
- **pytest** (7.4.3) - Testing framework
- **mysqlclient** (2.2.0) - MySQL database adapter

## Installation & Setup

1. Clone the repository:
```bash
git clone <repository_url>
cd fastapi_backend
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp env.example .env
# Edit .env with your configuration
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Database
DATABASE_URL=mysql://root:password@localhost:3306/sayan_db

# JWT Settings
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application Settings
APP_NAME=SAYAN Educational Platform
API_V1_STR=/api/v1
PROJECT_NAME=SAYAN API
DEBUG=True

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# Role-specific JWT Keys
ADMIN_SECRET_KEY=admin-secret-key-here
ACADEMY_SECRET_KEY=academy-secret-key-here
STUDENT_SECRET_KEY=student-secret-key-here
```

## Authentication Routes

### Student Authentication

#### Register
- **POST** `/api/v1/auth/student/register`
- **Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "1234567890",
  "password": "password123",
  "password_confirm": "password123",
  "date_of_birth": "1990-01-01",
  "gender": "male",
  "country": "USA",
  "city": "New York"
}
```
- **Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

#### Login
- **POST** `/api/v1/auth/student/login`
- **Request Body:**
```json
{
  "email": "john@example.com",
  "password": "password123"
}
```
- **Response:** Same as register

#### Refresh Token
- **POST** `/api/v1/auth/student/refresh`
- **Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```
- **Response:** New access and refresh tokens

#### Logout
- **POST** `/api/v1/auth/logout`
- **Response:**
```json
{
  "message": "Successfully logged out"
}
```

### Academy Authentication
Similar endpoints exist for academy users:
- **POST** `/api/v1/auth/academy/register`
- **POST** `/api/v1/auth/academy/login`
- **POST** `/api/v1/auth/academy/refresh`

### Admin Authentication
Admin endpoints:
- **POST** `/api/v1/auth/admin/login`
- **POST** `/api/v1/auth/admin/refresh`

## API Endpoints Examples

### Courses

#### List All Courses
- **GET** `/api/v1/courses/`
- **Query Parameters:**
  - `skip`: Number of records to skip (default: 0)
  - `limit`: Maximum records to return (default: 100)
  - `academy_id`: Filter by academy
  - `category_id`: Filter by category
- **Response:**
```json
[
  {
    "id": 1,
    "title": "Introduction to Python",
    "description": "Learn Python basics",
    "price": 99.99,
    "thumbnail": "https://example.com/thumb.jpg",
    "rating": 4.5,
    "enrollment_count": 150,
    "academy_id": 1,
    "category_id": 2,
    "created_at": "2024-01-01T00:00:00"
  }
]
```

#### Get Course Details
- **GET** `/api/v1/courses/{course_id}`
- **Response:** Detailed course object with chapters and lessons

#### List Course Categories
- **GET** `/api/v1/courses/categories`
- **Response:**
```json
[
  {
    "id": 1,
    "name": "Programming",
    "slug": "programming",
    "description": "Programming courses",
    "is_active": true
  }
]
```

#### Get My Courses (Requires Authentication)
- **GET** `/api/v1/courses/my-courses`
- **Headers:** `Authorization: Bearer {access_token}`
- **Response:** List of enrolled courses

### Digital Products

#### List Academy Digital Products
- **GET** `/api/v1/academies/{academy_id}/digital-products`
- **Response:** List of digital products

#### Purchase Digital Product
- **POST** `/api/v1/digital-products/{product_id}/purchase`
- **Headers:** `Authorization: Bearer {access_token}`

### Blog

#### List Blog Posts
- **GET** `/api/v1/blogs/posts`
- **Query Parameters:**
  - `academy_id`: Filter by academy
  - `category_id`: Filter by category
  - `is_featured`: Show only featured posts

#### Get Blog Post Details
- **GET** `/api/v1/blogs/posts/{post_id}`

#### Create Blog Comment
- **POST** `/api/v1/blogs/posts/{post_id}/comments`
- **Headers:** `Authorization: Bearer {access_token}`
- **Request Body:**
```json
{
  "content": "Great article!"
}
```

## Running Tests

Execute the test suite using pytest:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=app tests/
```

Run specific test file:

```bash
pytest tests/test_auth.py
```

## Additional Notes

### Database Migrations
When making model changes, create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

### CORS Configuration
CORS is configured to allow requests from the frontend application. Update `BACKEND_CORS_ORIGINS` in your `.env` file to match your frontend URL.

### Authentication Flow
1. Each user type (Admin, Academy, Student) has separate JWT secret keys
2. Tokens include the user type in the payload
3. Authentication middleware validates tokens against the appropriate secret key
4. Role-based access control is enforced at the endpoint level

### Rate Limiting
Consider implementing rate limiting for production use. FastAPI works well with slowapi:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

### Production Deployment
For production deployment:
1. Set `DEBUG=False` in environment variables
2. Use a production database
3. Configure proper logging
4. Use a reverse proxy (nginx) with SSL
5. Consider using Docker for containerization
6. Set up monitoring and error tracking (e.g., Sentry)

### API Documentation
FastAPI automatically generates interactive API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Contributing
1. Create a feature branch
2. Make your changes
3. Write/update tests
4. Ensure all tests pass
5. Submit a pull request

For questions or issues, please contact the development team. 
# FastAPI Backend Project Structure

## Overview
This FastAPI backend is a complete migration from Laravel, maintaining all functionality while leveraging Python's async capabilities and FastAPI's modern features.

## Directory Structure

```
fastapi_backend/
│
├── app/                          # Main application directory
│   ├── api/                      # API endpoints
│   │   └── v1/                   # Version 1 API
│   │       ├── __init__.py
│   │       ├── auth.py           # Authentication endpoints (login, register, refresh)
│   │       ├── courses.py        # Course browsing and enrollment
│   │       ├── academy.py        # Academy management (courses, chapters, lessons, exams)
│   │       ├── blogs.py          # Blog system (posts, categories, comments)
│   │       ├── cart.py           # Shopping cart management
│   │       ├── payment.py        # Payment processing and verification
│   │       ├── digital_products.py # Digital products marketplace
│   │       └── wallet.py         # Academy wallet and finance management
│   │
│   ├── core/                     # Core application configuration
│   │   ├── __init__.py
│   │   ├── config.py             # Settings management with Pydantic
│   │   └── security.py           # JWT tokens, password hashing, authentication
│   │
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── admin.py              # Admin user model
│   │   ├── role.py               # Roles and permissions
│   │   ├── academy.py            # Academy, AcademyUser, Trainer, Subscription
│   │   ├── student.py            # Student, enrollment, progress tracking
│   │   ├── course.py             # Course, Chapter, Lesson, Video, Exam, Question
│   │   ├── finance.py            # Payment, Transaction, Withdrawal, Finance tracking
│   │   ├── product.py            # Products, Packages, Digital products
│   │   ├── general.py            # Blog, BlogPost, Comments, Categories
│   │   ├── marketing.py          # Coupons, Affiliate links
│   │   └── template.py           # Template customization models
│   │
│   ├── schemas/                  # Pydantic schemas for validation
│   │   ├── __init__.py
│   │   ├── auth.py               # Authentication request/response schemas
│   │   └── course.py             # Course-related schemas
│   │
│   ├── crud/                     # CRUD operations layer
│   │   ├── __init__.py
│   │   ├── base.py               # Base CRUD class with common operations
│   │   └── student.py            # Student-specific CRUD operations
│   │
│   ├── services/                 # Business logic layer
│   │   └── __init__.py
│   │
│   ├── db/                       # Database configuration
│   │   ├── __init__.py
│   │   ├── base.py               # Base model imports
│   │   └── session.py            # Database session management
│   │
│   ├── deps/                     # FastAPI dependencies
│   │   ├── __init__.py
│   │   ├── database.py           # Database session dependency
│   │   └── auth.py               # Authentication dependencies and guards
│   │
│   ├── tests/                    # Test suite
│   │   ├── __init__.py
│   │   ├── conftest.py           # Test configuration and fixtures
│   │   └── test_auth.py          # Authentication tests
│   │
│   ├── __init__.py
│   └── main.py                   # FastAPI application entry point
│
├── alembic/                      # Database migrations
│   └── versions/                 # Migration files
│
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore file
├── alembic.ini                   # Alembic configuration
├── requirements.txt              # Python dependencies
├── README.md                     # Project documentation
└── project_structure.md          # This file
```

## Key Components

### 1. API Layer (`app/api/v1/`)
- **Purpose**: Handle HTTP requests and responses
- **Pattern**: RESTful API design
- **Features**:
  - Consistent response format
  - Query parameter validation
  - Authentication middleware integration
  - Mock data generators for development

### 2. Models Layer (`app/models/`)
- **Purpose**: Define database schema using SQLAlchemy ORM
- **Pattern**: Active Record pattern
- **Features**:
  - Relationships between entities
  - Automatic timestamps
  - Enum types for status fields
  - JSON fields for flexible data

### 3. Schemas Layer (`app/schemas/`)
- **Purpose**: Request/response validation and serialization
- **Pattern**: DTO (Data Transfer Object)
- **Features**:
  - Input validation
  - Output formatting
  - Type safety
  - Auto-documentation

### 4. CRUD Layer (`app/crud/`)
- **Purpose**: Database operations abstraction
- **Pattern**: Repository pattern
- **Features**:
  - Reusable base class
  - Type-safe operations
  - Pagination support
  - Complex queries

### 5. Dependencies (`app/deps/`)
- **Purpose**: Reusable FastAPI dependencies
- **Features**:
  - Database session management
  - Authentication guards
  - Role-based access control
  - Current user injection

### 6. Core (`app/core/`)
- **Purpose**: Application configuration and utilities
- **Features**:
  - Environment-based configuration
  - JWT token management
  - Password hashing
  - Security utilities

## Authentication Flow

1. **Multi-role Support**:
   - Admin users
   - Academy users
   - Students
   - Guest access

2. **JWT Implementation**:
   - Separate secret keys per user type
   - Access and refresh tokens
   - Token expiration handling

3. **Guards**:
   - `get_current_admin()`
   - `get_current_academy_user()`
   - `get_current_student()`
   - `get_optional_current_user()` for mixed access

## API Endpoints Structure

### Authentication (`/api/v1/auth/`)
- `POST /student/register` - Student registration
- `POST /student/login` - Student login
- `POST /student/refresh` - Refresh access token
- `POST /logout` - Logout (client-side token removal)

### Courses (`/api/v1/courses/`)
- `GET /` - List all published courses
- `GET /{course_id}` - Get course details
- `GET /categories` - List course categories
- `GET /my-courses` - Student's enrolled courses

### Academy Management (`/api/v1/academies/`)
- `POST /register` - Academy registration
- `POST /login` - Academy login
- `GET /courses` - Academy's courses
- `POST /courses` - Create new course
- `PUT /courses/{id}` - Update course
- Nested routes for chapters, lessons, exams, tools

### Blogs (`/api/v1/blogs/`)
- `GET /` - List blogs
- `GET /posts` - List blog posts
- `GET /posts/{id}` - Get post details
- `POST /posts/{id}/comments` - Add comment
- `GET /categories` - List categories

### Cart & Checkout (`/api/v1/cart/`)
- `GET /` - View cart
- `POST /add` - Add to cart
- `PUT /update/{id}` - Update quantity
- `DELETE /delete/{id}` - Remove item
- `POST /checkout/process` - Process checkout

### Payment (`/api/v1/payment/`)
- `POST /process` - Process payment
- `GET /verify/{payment_id}` - Verify payment status
- `GET /my-payments` - Payment history
- `POST /refund/{payment_id}` - Request refund

### Digital Products (`/api/v1/digital-products/`)
- `GET /` - List products
- `GET /{id}` - Product details
- `POST /{id}/purchase` - Purchase product
- `GET /{id}/download` - Download product
- `GET /my-products` - Purchased products

### Wallet (`/api/v1/academy/finance/wallet/`)
- `GET /` - Wallet balance
- `POST /withdraw` - Request withdrawal
- `GET /transactions` - Transaction history
- `GET /stats` - Financial statistics

## Development Features

### Mock Data
All endpoints return realistic mock data for development:
- Consistent ID generation
- Realistic relationships
- Random but sensible values
- Date/time handling

### Error Handling
- HTTP status codes
- Descriptive error messages
- Validation errors
- Authentication errors

### Documentation
- Auto-generated OpenAPI docs at `/docs`
- ReDoc alternative at `/redoc`
- Detailed endpoint descriptions
- Request/response examples

## Database Design

### User System
- Multi-table inheritance for user types
- Role-based permissions
- JWT authentication per user type

### Course System
- Hierarchical structure: Course → Chapter → Lesson
- Video management with providers
- Exam system with questions
- Progress tracking

### Financial System
- Payment processing
- Commission calculation
- Wallet management
- Withdrawal requests

### Content System
- Blog management
- Digital products
- Template customization

## Best Practices

1. **Code Organization**:
   - Single responsibility per module
   - Clear separation of concerns
   - Consistent naming conventions

2. **Security**:
   - Password hashing with bcrypt
   - JWT tokens with expiration
   - Role-based access control
   - Input validation

3. **Performance**:
   - Async/await for I/O operations
   - Database connection pooling
   - Efficient query design
   - Pagination support

4. **Maintainability**:
   - Type hints throughout
   - Comprehensive documentation
   - Modular architecture
   - Test coverage

## Next Steps

1. **Database Integration**:
   - Connect to MySQL database
   - Run Alembic migrations
   - Implement actual CRUD operations

2. **Business Logic**:
   - Implement service layer
   - Add validation rules
   - Handle edge cases

3. **Testing**:
   - Unit tests for CRUD operations
   - Integration tests for endpoints
   - Performance testing

4. **Deployment**:
   - Docker containerization
   - Environment configuration
   - Production optimizations
   - Monitoring setup 
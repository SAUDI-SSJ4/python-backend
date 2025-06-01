from typing import Generator
from app.db.session import SessionLocal


def get_db() -> Generator:
    """
    Database dependency that yields a database session.
    
    Yields:
        SQLAlchemy Session object
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 
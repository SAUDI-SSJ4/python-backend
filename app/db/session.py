from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Create engine for MySQL with improved connection handling
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_timeout=30,    # Timeout for getting connection from pool
    echo=settings.DEBUG,
    # Additional MySQL-specific settings
    connect_args={
        "connect_timeout": 60,
        "read_timeout": 60,
        "write_timeout": 60,
        "charset": "utf8mb4",
        "autocommit": False
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) 
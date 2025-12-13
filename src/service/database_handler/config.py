from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import settings

# Database configuration
#
# Default to storing the SQLite DB under ./data/tasks.db so it aligns with the
# task runner and attachment directory conventions (./data/...).
DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL.startswith("sqlite"):
    raise ValueError(
        "Only file-based SQLite is supported. "
        "Set DATABASE_URL to e.g. 'sqlite:///./data/tasks.db'."
    )

# Create engine with appropriate settings for SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # Set to True for SQL logging
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables defined in the models."""
    from .models import Base

    # Ensure the parent directory exists for sqlite file URLs.
    parsed = urlparse(DATABASE_URL)
    raw_path = parsed.path or ""
    if raw_path and raw_path != ":memory:":
        # urlparse() yields:
        # - sqlite:///relative/path.db  -> "/relative/path.db"
        # - sqlite:////absolute/path.db -> "//absolute/path.db"
        if raw_path.startswith("//"):
            db_path = raw_path[1:]  # keep absolute path (/abs/...)
        elif raw_path.startswith("/"):
            db_path = raw_path[1:]  # relative path (./rel/...)
        else:
            db_path = raw_path
        if db_path:
            Path(db_path).expanduser().resolve().parent.mkdir(
                parents=True, exist_ok=True
            )

    Base.metadata.create_all(bind=engine)


def get_db_session() -> Session:
    """Get a database session for direct use."""
    return SessionLocal()

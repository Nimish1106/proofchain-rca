from collections.abc import Generator
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """
    Create and cache the SQLAlchemy database engine.
    The connection is created lazily so the application
    can start even before PostgreSQL is configured.
    """
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Add it to the project-root .env file."
        )
    logger.info("Initializing database engine.")
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """
    Create and cache the SQLAlchemy session factory.
    """
    return sessionmaker(
        bind=get_engine(),
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.
    Each request receives its own database session.
    """
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

import logging
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.config import DATABASE_URL

logger = logging.getLogger(__name__)

# SQLite requires check_same_thread=False for multithreaded FastAPI requests
is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

logger.info(f"Initializing database connection (type: {'SQLite' if is_sqlite else 'PostgreSQL'})")

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI Dependency for database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Creates database tables if they do not exist."""
    logger.info("Verifying and creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Default SQLite database fallback inside the backend folder
DEFAULT_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ews_database.db")
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DB_FILE}"

# Retrieve DATABASE_URL from environment variables and handle empty strings safely
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or DATABASE_URL.strip() == "":
    DATABASE_URL = DEFAULT_DATABASE_URL


# SQLite-specific connection arguments for multithreading safety
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Setup the SQLAlchemy Core Engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

# Setup Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base model
Base = declarative_base()

def get_db():
    """Dependency injector utility for FastAPI router sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

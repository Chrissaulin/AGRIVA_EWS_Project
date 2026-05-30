import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database URL can be overridden via env var, default points to the PostgreSQL service defined in docker-compose.yml
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://agriva:agriva_pass@db:5432/agriva_db")

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI dependency that provides a DB session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

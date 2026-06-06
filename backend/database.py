import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

# Database URL can be overridden via env var, default points to the PostgreSQL service defined in docker-compose.yml
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://agriva_user:agriva_pass@db:5432/agriva_db")

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

# Initialize tables with retry to wait for DB readiness
def init_db(retries: int = 5, delay: int = 2):
    for attempt in range(1, retries + 1):
        try:
            # Test connection
            with engine.connect() as conn:
                pass
            # Import models after engine is ready to avoid circular import issues
            import models  # noqa: F401
            Base.metadata.create_all(bind=engine)
            print("[OK] Database tables initialized")
            return
        except OperationalError as e:
            print(f"[WARN] DB not ready (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(delay)
    raise RuntimeError("Failed to connect to the database after several attempts")

# Run initialization at import time
# init_db()


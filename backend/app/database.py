"""
PostgreSQL SQLAlchemy engine, session factory and declarative Base.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings


# ── Engine configuration ────────────────────────────────────────
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = "postgresql+psycopg://" + db_url[len("postgres://") :]
elif db_url.startswith("postgresql://"):
    db_url = "postgresql+psycopg://" + db_url[len("postgresql://") :]

engine = create_engine(
    db_url,
    echo=False,  # Disabled to prevent massive SQL query logs in the terminal
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """
    Wrap lock_timeout in try...except because PgBouncer and Neon
    connection poolers in transaction mode reject session-level SET commands.
    """
    try:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SET lock_timeout = '15s'")
        except Exception:
            pass
        finally:
            cursor.close()
    except Exception:
        pass


# ── Session factory ─────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Declarative base ───────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency for FastAPI routes ───────────────────────────────
def get_db():
    """Yield a database session, close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

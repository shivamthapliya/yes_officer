from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from api.config.settings import settings


def _normalize_url(url: str) -> str:
    # Use the psycopg 3 driver regardless of how the URL was written.
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


engine = create_engine(
    _normalize_url(settings.DATABASE_URL),
    pool_size=settings.DB_POOL_SIZE,
    pool_pre_ping=True,
    echo=settings.DB_ECHO,
)


@event.listens_for(engine, "connect")
def _use_utc(dbapi_connection, _record):
    # Return every TIMESTAMPTZ in UTC regardless of the server's local timezone.
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET TIME ZONE 'UTC'")
    dbapi_connection.commit()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

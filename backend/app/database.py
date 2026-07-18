from collections.abc import Generator

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


# URL.create safely handles special characters in database credentials.
database_url = URL.create(
    drivername="postgresql+psycopg",
    username=settings.postgres_user,
    password=settings.postgres_password,
    host=settings.postgres_host,
    port=settings.postgres_port,
    database=settings.postgres_db,
)


# The engine manages the pool of connections between SQLAlchemy and PostgreSQL.
engine = create_engine(database_url)


# Each API request receives its own database session from this factory.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session and close it after the request finishes."""

    with SessionLocal() as session:
        yield session

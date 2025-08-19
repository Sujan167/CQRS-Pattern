import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


READ_DB_SYNC_URL = os.getenv(
    "READ_DB_SYNC_URL",
    # Use sync driver for Celery worker interactions with read DB
    os.getenv("READ_DB_URL", "postgresql+psycopg2://postgres:postgres@read_db:5432/read_db").replace(
        "+asyncpg", "+psycopg2"
    ),
)


engine = create_engine(
    READ_DB_SYNC_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_timeout=30,
    future=True,
)


SyncSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)



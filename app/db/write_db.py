# app/db/write_db.py

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

WRITE_DB_URL = os.getenv("WRITE_DB_URL", "postgresql+asyncpg://postgres:postgres@write_db:5432/write_db")

async_engine = create_async_engine(
    WRITE_DB_URL,
    echo=True,
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_pre_ping=True       #Check before using a connection
)

async_write_session = sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession
)

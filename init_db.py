# init_db.py
import asyncio
from app.db.models import Base
from app.db.write_db import async_engine as write_engine
from app.db.read_db import async_engine as read_engine

async def create_tables():
    async with write_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Write DB tables created.")

    async with read_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Read DB tables created.")

if __name__ == "__main__":
    asyncio.run(create_tables())

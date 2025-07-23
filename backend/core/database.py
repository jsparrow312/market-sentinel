import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .config import settings

# Setup for PostgreSQL
# engine = create_async_engine(settings.DATABASE_URL, echo=False)
# AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Setup for Redis Cache
redis_cache = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

# async def get_db():
#     """Dependency to get a database session."""
#     async with AsyncSessionLocal() as session:
#         yield session

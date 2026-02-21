from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
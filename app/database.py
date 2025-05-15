from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_async_engine(
    settings.db_uri,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal: sessionmaker[AsyncSession] = sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_db():
    """
    FastAPI dependency: yields an AsyncSession, then
    commits on success or rolls back on exception, and closes.
    """
    session: AsyncSession = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except:
        await session.rollback()
        raise
    finally:
        await session.close()

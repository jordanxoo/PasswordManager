from sqlalchemy.ext.asyncio import create_async_engine,AsyncSession
from sqlalchemy.orm import sessionmaker,declarative_base
from app.config import settings

#print("DB URL w database.py:", settings.DATABASE_URL) 
DATABASE_URL  = settings.DATABASE_URL
DATABASE_URL = DATABASE_URL.replace("postgresql://","postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL)

AsyncSessionLocal = sessionmaker(engine,class_=AsyncSession,expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from pathlib import Path
from models import Base

# Загружаем .env для DATABASE_URL
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)
Session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Все таблицы пересозданы!")

if __name__ == "__main__":
    asyncio.run(main())

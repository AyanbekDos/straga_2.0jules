import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from sqlalchemy.future import select
from semantic_text_splitter import TextSplitter
import re

# Импортируем модели и соединение с БД из централизованных модулей
from models.models import Page, Chunk, Link, DatasetSettings
from core.db import async_session_maker

def flatten(text):
    return re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()

async def get_chunk_settings(session, dataset_id):
    # Получаем настройки чанкирования из dataset_settings
    result = await session.execute(
        select(DatasetSettings).where(DatasetSettings.dataset_id == dataset_id)
    )
    settings = result.scalar_one_or_none()
    chunk_size = settings.chunk_size if settings and settings.chunk_size else 512
    chunk_overlap = settings.chunk_overlap if settings and settings.chunk_overlap else 50
    return chunk_size, chunk_overlap

async def chunk_texts(dataset_id: int):
    async with async_session_maker() as session:
        chunk_size, chunk_overlap = await get_chunk_settings(session, dataset_id)
        print(f"🧩 chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")

        # Находим все pages с заполненным clean_text, где еще нет чанков
        result = await session.execute(
            select(Page)
            .join(Link)
            .where(Link.dataset_id == dataset_id)
            .where(Page.clean_text.isnot(None))
        )
        pages = result.scalars().all()
        if not pages:
            print("⚠️ Нет страниц для чанкирования.")
            return

        splitter = TextSplitter.from_tiktoken_model("gpt-3.5-turbo", chunk_size)
        total_chunks = 0

        for page in pages:
            text = flatten(page.clean_text)
            chunks = splitter.chunks(text)
            for idx, chunk_text in enumerate(chunks):
                session.add(Chunk(
                    page_id=page.id,
                    chunk_index=idx,
                    chunk_text=chunk_text
                ))
            total_chunks += len(chunks)
            print(f"✅ {page.url[:50]} — чанков: {len(chunks)}")
            await session.commit()  # Можно вынести за цикл для скорости

        print(f"\n✅ Готово! Сгенерировано чанков: {total_chunks}")

if __name__ == "__main__":
    import sys
    dataset_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    asyncio.run(chunk_texts(dataset_id))

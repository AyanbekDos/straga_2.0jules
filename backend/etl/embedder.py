import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from openai import AsyncOpenAI

# Импортируем модели и соединение с БД из централизованных модулей
from models.models import Chunk, Embedding, DatasetSettings, Page, Link
from core.db import async_session_maker

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def build_input(chunk: Chunk, settings: DatasetSettings):
    parts = [chunk.chunk_text]
    if getattr(settings, "use_author", False) and chunk.clean_author:
        parts.append(f"Author: {chunk.clean_author}")
    if getattr(settings, "use_summary", False) and chunk.summary:
        parts.append(f"Summary: {chunk.summary}")
    return "\n".join(parts)

async def embedder(dataset_id: int, batch_size: int = 50):
    async with async_session_maker() as session:
        # Получаем настройки
        settings_q = await session.execute(
            select(DatasetSettings).where(DatasetSettings.dataset_id == dataset_id)
        )
        settings = settings_q.scalar_one_or_none()
        embedding_model = "text-embedding-3-small"

        # Чанки без эмбеддингов
        result = await session.execute(
            select(Chunk)
            .options(selectinload(Chunk.page).selectinload(Page.link))
            .where(~Chunk.id.in_(select(Embedding.chunk_id)))
        )
        all_chunks = [c for c in result.scalars() if c.page.link.dataset_id == dataset_id]
        total = len(all_chunks)
        print(f"🤖 Чанков без векторов: {total}")

        for i in range(0, total, batch_size):
            batch = all_chunks[i:i+batch_size]
            inputs = [await build_input(chunk, settings) for chunk in batch]
            response = await client.embeddings.create(input=inputs, model=embedding_model)
            vectors = [v.embedding for v in response.data]

            for chunk, inp, vec in zip(batch, inputs, vectors):
                session.add(Embedding(
                    chunk_id=chunk.id,
                    input=inp,
                    vector=vec
                ))
            await session.commit()
            print(f"✅ {i + len(batch)}/{total} векторизовано")

if __name__ == "__main__":
    import sys
    dataset_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    asyncio.run(embedder(dataset_id))

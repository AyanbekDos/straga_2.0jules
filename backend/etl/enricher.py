import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import json
from dotenv import load_dotenv
from sqlalchemy.future import select

# Импортируем модели и соединение с БД из централизованных модулей
from models.models import Chunk, Page, Link, DatasetSettings
from core.db import async_session_maker
from openai import AsyncOpenAI

# 🌍 ENV
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 🚀 INIT
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def enrich_chunk(chunk, summary_prompt, gpt_model, session):
    prompt = f"""{summary_prompt}

Вот текст:
{chunk.chunk_text}

Ответь JSON:
{{
  "summary": "...",
  "topics": ["...", "..."]
}}"""

    try:
        response = await client.chat.completions.create(
            model=gpt_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
        )
        content = response.choices[0].message.content
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            print(f"❌ JSON decode error в chunk {chunk.id}:\n{content}")
            chunk.quality = "needs_review"
            session.add(chunk)
            return

        summary = parsed.get("summary", "").strip()
        topics = parsed.get("topics", [])

        chunk.summary = summary
        chunk.chunk_meta_data = {
            **(chunk.chunk_meta_data or {}),
            "topics": topics
        }

        # ✅ Проверка качества
        if not summary or len(summary.split()) < 10:
            chunk.quality = "needs_review"
        elif not topics or all(len(t) < 3 for t in topics):
            chunk.quality = "needs_review"
        elif summary.lower().startswith(("в этом тексте", "данный текст")):
            chunk.quality = "needs_review"
        else:
            chunk.quality = "ok"

        session.add(chunk)
        print(f"✅ enriched chunk {chunk.id}, quality = {chunk.quality}")

    except Exception as e:
        print(f"❌ GPT error в chunk {chunk.id}: {e}")
        chunk.quality = "needs_review"
        session.add(chunk)

async def enrich_chunks(dataset_id: int, batch_size: int = 10):
    async with async_session_maker() as session:
        # Загружаем настройки
        settings_result = await session.execute(
            select(DatasetSettings).where(DatasetSettings.dataset_id == dataset_id)
        )
        settings = settings_result.scalar_one_or_none()
        if not settings:
            print(f"❌ Настройки не найдены для dataset_id={dataset_id}")
            return

        # Загружаем чанки без summary
        result = await session.execute(
            select(Chunk)
            .join(Chunk.page)
            .join(Page.link)
            .where(Link.dataset_id == dataset_id)
            .where(Chunk.summary.is_(None))
            .limit(batch_size)
        )
        chunks = result.scalars().all()

        if not chunks:
            print("🔍 Нет чанков для enrichment.")
            return

        for chunk in chunks:
            await enrich_chunk(chunk, settings.summary_prompt, settings.gpt_model, session)

        await session.commit()
        print("🏁 Обогащение завершено!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❗ Укажи dataset_id")
        sys.exit(1)

    dataset_id = int(sys.argv[1])
    asyncio.run(enrich_chunks(dataset_id))

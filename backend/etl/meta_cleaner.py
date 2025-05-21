import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv
from sqlalchemy import select, or_

# Импортируем модели и соединение с БД из централизованных модулей
from models.models import Page, Link, DatasetSettings
from core.db import async_session_maker

# Загружаем переменные окружения
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Настраиваем OpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def gpt_clean(text: str, prompt: str, model: str) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt.format(text=text)}],
        max_tokens=32,
        temperature=0
    )
    return response.choices[0].message.content.strip()

async def process_pages(dataset_id: int):
    async with async_session_maker() as session:
        # Получаем настройки
        settings_q = await session.execute(
            select(DatasetSettings).where(DatasetSettings.dataset_id == dataset_id)
        )
        settings = settings_q.scalar_one_or_none()
        model = settings.gpt_model if settings else "gpt-3.5-turbo"
        prompt = "Приведи в чистый и короткий вид: \"{text}\""

        # Получаем страницы с неочищенными полями
        result = await session.execute(
            select(Page)
            .join(Link, Link.id == Page.link_id)
            .where(Link.dataset_id == dataset_id)
            .where(
                or_(
                    Page.clean_author.is_(None) & Page.raw_author.isnot(None) & (~Page.author_needs_review),
                    Page.clean_date.is_(None) & Page.raw_date.isnot(None) & (~Page.date_needs_review),
                    Page.clean_category.is_(None) & Page.raw_category.isnot(None) & (~Page.category_needs_review)
                )
            )
            .limit(20)
        )
        pages = result.scalars().all()

        if not pages:
            print("✅ Нет страниц для очистки.")
            return

        for page in pages:
            print(f"🧼 Страница: {page.url}")
            if page.raw_author and not page.clean_author and not page.author_needs_review:
                page.clean_author = await gpt_clean(page.raw_author, prompt, model)

            if page.raw_date and not page.clean_date and not page.date_needs_review:
                try:
                    parsed_date = datetime.fromisoformat(page.raw_date)
                    page.clean_date = parsed_date
                except Exception:
                    page.date_needs_review = True

            if page.raw_category and not page.clean_category and not page.category_needs_review:
                page.clean_category = await gpt_clean(page.raw_category, prompt, model)

            session.add(page)

        await session.commit()
        print("✅ Все страницы обработаны.")

if __name__ == "__main__":
    dataset_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    asyncio.run(process_pages(dataset_id))

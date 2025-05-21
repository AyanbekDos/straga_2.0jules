import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from sqlalchemy.future import select
from bs4 import BeautifulSoup
import trafilatura

# Импортируем модели и соединение с БД из централизованных модулей
from models.models import Page
from core.db import async_session_maker

def extract_clean_text(html: str) -> str:
    # Пробуем через trafilatura (часто лучший вариант)
    clean = trafilatura.extract(html)
    if clean and len(clean.strip()) > 50:
        return clean.strip()
    # Fallback: BeautifulSoup
    soup = BeautifulSoup(html, 'lxml')
    text = soup.get_text(separator=' ', strip=True)
    return text if len(text) > 50 else ""

async def clean_pages(dataset_id: int, batch_size: int = 20):
    async with async_session_maker() as session:
        # Находим все страницы с пустым clean_text по датасету
        result = await session.execute(
            select(Page)
            .where(Page.clean_text.is_(None))
            .where(Page.link.has(dataset_id=dataset_id))
            .limit(batch_size)
        )
        pages = result.scalars().all()
        if not pages:
            print("🔍 Нет страниц для чистки.")
            return

        for page in pages:
            clean = extract_clean_text(page.raw_html)
            if clean:
                page.clean_text = clean
                print(f"✅ cleaned: {page.url[:60]}")
            else:
                print(f"⚠️ пусто: {page.url[:60]}")

        await session.commit()

if __name__ == "__main__":
    import sys
    dataset_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    asyncio.run(clean_pages(dataset_id))

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from datetime import datetime
from sqlalchemy import select
import re

# Импортируем модели и соединение с БД из централизованных модулей
from models.models import Link
from core.db import get_db

router = APIRouter()

# 🔁 Чистая функция
def normalize_url(url: str) -> str:
    return re.sub(r"\?.*", "", url.strip())

async def _insert_links(dataset_id: int, urls: list[str], session: AsyncSession) -> int:
    normalized_urls = list(set([normalize_url(url) for url in urls]))

    existing = await session.execute(
        select(Link.url).where(Link.dataset_id == dataset_id, Link.url.in_(normalized_urls))
    )
    existing_urls = set([row[0] for row in existing.all()])

    new_links = [
        Link(dataset_id=dataset_id, url=url, status="queued", created_at=datetime.utcnow())
        for url in normalized_urls if url not in existing_urls
    ]

    session.add_all(new_links)
    await session.flush()
    return len(new_links)

# 🌐 FastAPI-роут (если нужен)
@router.post("/datasets/{dataset_id}/links")
async def insert_links_api(
    dataset_id: int,
    body: dict,
    session: AsyncSession = Depends(get_db)
):
    urls = body.get("urls")
    if not urls or not isinstance(urls, list):
        raise HTTPException(status_code=400, detail="Нужен список ссылок")

    count = await _insert_links(dataset_id, urls, session)
    # Нет необходимости вызывать commit, так как get_db автоматически делает commit при завершении
    return {"inserted": count}

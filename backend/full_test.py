# full_test.py
import os
import sys
import asyncio
import subprocess
import logging
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

env_path = Path(__file__).resolve().parent / ".env"
print(f"📂 Loading .env from: {env_path}")
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL не найден в .env")
print(f"🚨 DATABASE_URL = {DATABASE_URL}")

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from models import Dataset, Link, Chunk, Embedding, Page, DatasetSettings
from etl.insert_links import _insert_links

engine = create_async_engine(DATABASE_URL, echo=False)
Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

TEST_URLS = [
    "https://www.advantshop.net/blog/prodvizhenie-v-sotsialnykh-setyakh/kak-pisat-posty-chtoby-ikh-chitali",
    "https://smmplanner.com/blog/kak-pisat-tekst-dlya-postov-v-socialnyh-setyah/",
    "https://www.likeni.ru/analytics/polnyy-gid-po-napisaniyu-postov-v-sotssetyakh-pravila-idei-i-primery/",
    "https://sostav.ru/blogs/278699/59040",
    "https://onlypult.com/ru/blog/kopirayting-sovety",
    "https://willskill.ru/blog/stati/marketing/8-sekretov-chtoby-napisat-horoshij-post-dlya-soczsetej",
    "https://9writer.ru/blog/10_sovetov_po_napisaniyu_postov",
    "https://lifehacker.ru/kak-oformit-post-v-socsetyax/",
    "https://vc.ru/marketing/1759679-kopiraiting-v-socialnyh-setyah-10-sekretov-kotorymi-polzuyutsya-vliyatelnye-lyudi",
    "https://synergy.ru/akademiya/management/kak_napisat_post_dlya_soczialnyix_setej",
    "https://buffer.com/resources/copywriting-formulas/",
    "https://copyblogger.com/social-media-copywriting/",
    "https://www.sprinklr.com/blog/social-media-copywriting/",
    "https://www.portent.com/blog/paid-social/how-to-write-social-media-ad-copy-that-converts.htm",
    "https://blog.hubspot.com/marketing/social-media-copywriting"
]

async def create_dataset() -> int:
    async with Session() as session:
        ds = Dataset(user_id=1, name="TEST PIPE", description="Автотест пайплайна")
        session.add(ds)
        await session.flush()

        # Добавляем настройки
        settings = DatasetSettings(
            dataset_id=ds.id,
            chunk_size=600,
            chunk_overlap=100,
            summary_prompt="Сделай краткое резюме чанка.",
            metadata_targets={"author": "строка автора", "date": "дата статьи"},
            gpt_model="gpt-3.5-turbo"
        )
        session.add(settings)

        await _insert_links(ds.id, TEST_URLS, session=session)
        await session.commit()

        print(f"🆕 Dataset создан (id={ds.id})")
        return ds.id

def run_stage(script: str, args: list[str]):
    short_names = {
        "raw_html_extractor": "📅 Скачивание",
        "clean_text_extractor": "🧹 Очистка",
        "chunker": "🧹 Чанки",
        "qc_chunks": "🪪 QC",
        "meta_cleaner": "🧼 Метаданные",
        "enricher": "🧠 Обогащение",
        "embedder": "🔗 Эмбеддинги",
    }
    title = short_names.get(script, script)
    print(f"{title}... ", end="", flush=True)
    try:
        subprocess.run([sys.executable, f"etl/{script}.py", *args], check=True)
        print("✅")
    except subprocess.CalledProcessError:
        print("❌")
        raise

async def print_summary(dataset_id: int):
    async with Session() as session:
        links = (await session.execute(select(Link).where(Link.dataset_id == dataset_id))).scalars().all()
        chunks = (await session.execute(
            select(Chunk).join(Chunk.page).join(Page.link).where(Link.dataset_id == dataset_id)
        )).scalars().all()
        embeddings = (await session.execute(
            select(Embedding).join(Embedding.chunk).join(Chunk.page).join(Page.link).where(Link.dataset_id == dataset_id)
        )).scalars().all()

        bad_links = [l for l in links if l.status == "error_fetch"]
        print(f"""
📊 Результаты пайплайна
🗂 Dataset ID:      {dataset_id}
🔗 Ссылок всего:    {len(links)}
❌ Ошибок fetch:     {len(bad_links)}
🧹 Чанков:          {len(chunks)}
📈 Эмбеддингов:     {len(embeddings)}
""")

async def main():
    print("🚀 Запуск полного пайплайна...")
    dataset_id = await create_dataset()

    try:
        run_stage("raw_html_extractor", [str(dataset_id)])
        run_stage("clean_text_extractor", [str(dataset_id)])
        run_stage("chunker", [str(dataset_id)])
        run_stage("qc_chunks", [str(dataset_id)])
        run_stage("meta_cleaner", [str(dataset_id)])
        run_stage("enricher", [str(dataset_id)])
        run_stage("embedder", [str(dataset_id)])
    except Exception as e:
        print(f"❗ Ошибка пайплайна: {e}")
    await print_summary(dataset_id)

if __name__ == "__main__":
    asyncio.run(main())

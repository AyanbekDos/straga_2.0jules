import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import aiohttp
import trafilatura
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from langdetect import detect
import re
from datetime import datetime

from sqlalchemy.future import select

# Импортируем модели и соединение с БД из централизованных модулей
from models.models import Link, Page
from core.db import async_session_maker

# ======= HELPERS =======
def parse_custom_date(date_str):
    try:
        date_str = ' '.join(date_str.split())
        date_str = re.sub(r'^(Updated|Published|Posted|Date):?\s*', '', date_str)
        return dateparser.parse(date_str)
    except Exception:
        return None

def parse_meta(html, url):
    soup = BeautifulSoup(html, 'lxml')
    data = {
        'url': url,
        'title': '',
        'raw_date': '',
        'raw_author': '',
        'raw_category': '',
        'language': '',
        'meta_data': {}
    }

    # Title
    if soup.title and soup.title.string:
        data['title'] = soup.title.string.strip()
        data['meta_data']['title_source'] = 'title'

    # Date
    meta_date = soup.find('meta', property='article:published_time')
    if meta_date and meta_date.get('content'):
        parsed = parse_custom_date(meta_date['content'])
        if parsed:
            data['raw_date'] = parsed.isoformat()
            data['meta_data']['date_source'] = 'article:published_time'

    # Author
    meta_author = soup.find('meta', attrs={'name': 'author'})
    if meta_author and meta_author.get('content'):
        data['raw_author'] = meta_author['content'].strip()
        data['meta_data']['author_source'] = 'meta[name=author]'

    # Category
    meta_category = soup.find('meta', attrs={'name': 'category'})
    if meta_category and meta_category.get('content'):
        data['raw_category'] = meta_category['content'].strip()
        data['meta_data']['category_source'] = 'meta[name=category]'

    # Language
    html_lang = soup.find('html')
    if html_lang and html_lang.get('lang'):
        data['language'] = html_lang['lang'].split('-')[0]
        data['meta_data']['language_source'] = 'html[lang]'
    else:
        try:
            body = trafilatura.extract(html) or ''
            data['language'] = detect(body)
            data['meta_data']['language_source'] = 'langdetect'
        except Exception as e:
            data['meta_data']['language_error'] = str(e)

    return data

async def fetch_html(session, url):
    headers = {
        'User-Agent': 'Mozilla/5.0',
    }
    try:
        async with session.get(url, headers=headers, timeout=30) as resp:
            html = await resp.text()
            return resp.status, html
    except Exception as e:
        print(f"[ERROR] {url}: {e}")
        return None, None

# ======= MAIN =======
async def main(dataset_id: int):
    print(f"🔍 Загружаем queued ссылки для dataset_id={dataset_id} ...")
    async with async_session_maker() as db:
        result = await db.execute(
            select(Link).where(Link.dataset_id == dataset_id, Link.status == "queued")
        )
        links = result.scalars().all()

        if not links:
            print("⚠️ Нет queued ссылок для обработки.")
            return

        print(f"🕸️ Всего ссылок для скачивания: {len(links)}")
        timeout = aiohttp.ClientTimeout(total=60)
        connector = aiohttp.TCPConnector(limit=5, ssl=False)

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            for link in links:
                url = link.url
                print(f"➡️ Качаю: {url}")
                status, html = await fetch_html(session, url)
                link.last_attempt_at = datetime.utcnow()
                link.http_code = status

                if not html or status != 200:
                    link.status = "error_fetch"
                    await db.commit()
                    print(f"  ❌ Ошибка загрузки")
                    continue

                meta = parse_meta(html, url)

                # --- Review эвристики
                author_needs_review = not meta['raw_author'] or meta['raw_author'].isdigit()
                date_needs_review = not meta['raw_date'] or "T" not in meta['raw_date']
                category_needs_review = not meta.get('raw_category')

                page = Page(
                    link_id=link.id,
                    url=url,
                    title=meta['title'],
                    raw_html=html,
                    raw_author=meta['raw_author'],
                    raw_date=meta['raw_date'],
                    raw_category=meta['raw_category'],
                    meta_data=meta['meta_data'],
                    clean_text=None,
                    clean_author=None,
                    clean_date=None,
                    clean_category=None,
                    author_needs_review=author_needs_review,
                    date_needs_review=date_needs_review,
                    category_needs_review=category_needs_review,
                )
                db.add(page)
                link.status = "fetched"
                await db.commit()
                print(f"  ✅ Сохранено: {meta['title'][:60] if meta['title'] else url[:60]}")
                await asyncio.sleep(1)

    print("✅ Все ссылки обработаны!")

if __name__ == "__main__":
    import sys
    dataset_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    asyncio.run(main(dataset_id))

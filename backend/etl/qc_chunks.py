import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import json
from sqlalchemy import select, func
from openai import AsyncOpenAI
from rich import print as rprint
from dotenv import load_dotenv

# Импортируем модели и соединение с БД из централизованных модулей
from models.models import Chunk, Page, Link, DatasetSettings
from core.db import async_session_maker

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def run_qc(dataset_id: int):
    async with async_session_maker() as session:
        # Получаем модель из DatasetSettings
        settings_result = await session.execute(
            select(DatasetSettings.gpt_model).where(DatasetSettings.dataset_id == dataset_id)
        )
        model = settings_result.scalar_one_or_none() or "gpt-3.5-turbo"

        # Берём 10 случайных чанков
        result = await session.execute(
            select(Chunk)
            .join(Page, Page.id == Chunk.page_id)
            .join(Link, Link.id == Page.link_id)
            .where(Link.dataset_id == dataset_id)
            .order_by(func.random())
            .limit(10)
        )
        chunks = result.scalars().all()

        if not chunks:
            rprint("[bold red]❌ Нет чанков для проверки.[/bold red]")
            return

        # Собираем JSON для GPT
        gpt_input = []
        for chunk in chunks:
            sentences = chunk.chunk_text.split(". ")
            head = ". ".join(sentences[:3])
            tail = ". ".join(sentences[-3:])
            gpt_input.append({
                "chunk_id": chunk.id,
                "sample": f"Начало чанка id={chunk.id}:\n{head}...\n...\nКонец чанка id={chunk.id}:\n{tail}"
            })

        # Промпт
        prompt = [
            {"role": "system", "content": "Ты — редактор chunk-мастерской. Твоя задача — проверить, насколько логично обрезаны куски текста. Если начало и конец выглядят обрубленными, пометь как bad. Верни JSON со списком: [{chunk_id: ..., verdict: 'good' | 'bad'}]"},
            {"role": "user", "content": json.dumps(gpt_input, ensure_ascii=False)}
        ]

        # GPT вызов
        rprint(f"[bold magenta]🤖 Модель:[/bold magenta] {model}")
        response = await client.chat.completions.create(model=model, messages=prompt)
        reply = response.choices[0].message.content.strip()

        try:
            parsed = json.loads(reply)
        except Exception as e:
            rprint("[bold red]❌ Ошибка разбора ответа GPT:[/bold red]", e)
            print(reply)
            return

        bad_count = sum(1 for item in parsed if item["verdict"] == "bad")
        total = len(parsed)
        bad_ratio = bad_count / total

        rprint(f"\n📋 [bold cyan]Результаты QC:[/bold cyan] {bad_count} из {total} — bad ({bad_ratio:.0%})")

        if bad_ratio > 0.3:
            rprint("[bold red]⚠️ Слишком много плохих чанков — стоит пересмотреть размер chunk_size или chunk_overlap[/bold red]")

if __name__ == "__main__":
    asyncio.run(run_qc(int(sys.argv[1])))

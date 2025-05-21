import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import os
import openai
from sqlalchemy import select, update

# Импортируем модели и соединение с БД из централизованных модулей
from models.models import Dataset
from core.db import async_session_maker
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

MODEL = "gpt-4"  # или "gpt-4o", или "gpt-3.5-turbo"

PROMPT = """
Ты — AI-ассистент, который помогает составить рекомендации для извлечения данных из текста.

Вот описание датасета:
"{name}" — {description}

На основе этого:
1. Предложи, какие **метаданные** можно выделить (максимум 5).
2. Предложи 2–3 **инструкции (промпта)**, что можно сделать с каждым текстом (summary, выводы, эмоции и т.д.)

Ответ верни строго в JSON:
{{
  "meta_fields": ["", "", ...],
  "prompts": ["", "", ...]
}}
"""

async def generate_prompts(dataset: Dataset):
    content = PROMPT.format(name=dataset.name, description=dataset.description or "")
    response = await openai.ChatCompletion.acreate(
        model=MODEL,
        messages=[{"role": "user", "content": content}],
        temperature=0.4,
        max_tokens=600
    )
    text = response.choices[0].message.content
    print("🤖 GPT ответ:\n", text)

    try:
        parsed = eval(text, {"__builtins__": None}, {})
    except Exception as e:
        print(f"❌ Ошибка парсинга JSON от GPT: {e}")
        return None

    return parsed

async def run(dataset_id: int):
    async with async_session_maker() as session:
        result = await session.execute(select(Dataset).where(Dataset.id == dataset_id))
        dataset = result.scalar()

        if not dataset:
            print("❌ Dataset не найден")
            return

        print(f"🎥 Работаем с датасетом: {dataset.name}")
        gpt_result = await generate_prompts(dataset)
        if not gpt_result:
            return

        # Обновим JSONB-поля
        await session.execute(
            update(Dataset)
            .where(Dataset.id == dataset_id)
            .values(
                embedding_settings={"meta_fields": gpt_result["meta_fields"]},
                prompt_templates={"prompts": gpt_result["prompts"]}
            )
        )
        await session.commit()
        print("✅ Датасет обновлён!")

if __name__ == "__main__":
    import sys
    dataset_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    asyncio.run(run(dataset_id))

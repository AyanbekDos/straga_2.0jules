from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List

from db import get_session
from models import Dataset, DatasetSettings

router = APIRouter(prefix="/datasets", tags=["Datasets"])

# 🧱 Схемы
class CreateDatasetRequest(BaseModel):
    name: str
    description: str

class RecommendationResponse(BaseModel):
    meta_fields: List[dict]
    recommended_chunk_size: int
    recommended_chunk_overlap: int

class UpdateSettingsRequest(BaseModel):
    chunk_size: int
    chunk_overlap: int
    summary_prompt: str
    gpt_model: str
    metadata_targets: dict

# 📌 Создание датасета
@router.post("/")
async def create_dataset(data: CreateDatasetRequest, session: AsyncSession = Depends(get_session)):
    dataset = Dataset(
        name=data.name,
        description=data.description,
        user_id=1  # ⚠️ пока захардкожено
    )
    session.add(dataset)
    await session.flush()
    await session.commit()
    return {"id": dataset.id}

# 💡 Получение рекомендаций
@router.get("/{dataset_id}/recommendations", response_model=RecommendationResponse)
async def get_recommendations(dataset_id: int, session: AsyncSession = Depends(get_session)):
    # ⚙️ Заглушка. Позже будет вызов OpenAI с промтом.
    return RecommendationResponse(
        meta_fields=[
            {"name": "тема", "prompt": "Определи главную тему этого фрагмента."},
            {"name": "тональность", "prompt": "Определи тональность текста."}
        ],
        recommended_chunk_size=600,
        recommended_chunk_overlap=100
    )

# 💾 Сохранение настроек
@router.post("/{dataset_id}/settings")
async def update_settings(dataset_id: int, data: UpdateSettingsRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(DatasetSettings).where(DatasetSettings.dataset_id == dataset_id))
    settings = result.scalar_one_or_none()

    if settings:
        settings.chunk_size = data.chunk_size
        settings.chunk_overlap = data.chunk_overlap
        settings.summary_prompt = data.summary_prompt
        settings.metadata_targets = data.metadata_targets
        settings.gpt_model = data.gpt_model
    else:
        settings = DatasetSettings(
            dataset_id=dataset_id,
            chunk_size=data.chunk_size,
            chunk_overlap=data.chunk_overlap,
            summary_prompt=data.summary_prompt,
            metadata_targets=data.metadata_targets,
            gpt_model=data.gpt_model
        )
        session.add(settings)

    await session.commit()
    return {"status": "ok"}

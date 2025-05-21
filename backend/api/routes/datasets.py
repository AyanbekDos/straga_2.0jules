from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from core.db import get_db
from core.security import get_current_user
from models.models import Dataset as DatasetModel, DatasetSettings as DatasetSettingsModel
from api.schemas.datasets import (
    DatasetCreate, DatasetUpdate, Dataset,
    DatasetSettingsCreate, DatasetSettingsUpdate, RecommendationResponse
)

router = APIRouter(prefix="/datasets", tags=["Datasets"])

@router.post("/", response_model=Dataset, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    data: DatasetCreate, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    dataset = DatasetModel(
        name=data.name,
        description=data.description,
        user_id=current_user.id
    )
    db.add(dataset)
    await db.flush()
    await db.refresh(dataset)
    return dataset

@router.get("/{dataset_id}/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    dataset_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Проверка доступа к датасету
    result = await db.execute(
        select(DatasetModel).where(
            DatasetModel.id == dataset_id,
            DatasetModel.user_id == current_user.id
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    # Заглушка. Позже будет вызов OpenAI с промтом.
    return RecommendationResponse(
        meta_fields=[
            {"name": "тема", "prompt": "Определи главную тему этого фрагмента."},
            {"name": "тональность", "prompt": "Определи тональность текста."}
        ],
        recommended_chunk_size=600,
        recommended_chunk_overlap=100
    )

@router.post("/{dataset_id}/settings")
async def update_settings(
    dataset_id: int, 
    data: DatasetSettingsUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Проверка доступа к датасету
    result = await db.execute(
        select(DatasetModel).where(
            DatasetModel.id == dataset_id,
            DatasetModel.user_id == current_user.id
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    result = await db.execute(select(DatasetSettingsModel).where(DatasetSettingsModel.dataset_id == dataset_id))
    settings = result.scalar_one_or_none()

    if settings:
        # Обновляем только переданные поля
        if data.chunk_size is not None:
            settings.chunk_size = data.chunk_size
        if data.chunk_overlap is not None:
            settings.chunk_overlap = data.chunk_overlap
        if data.summary_prompt is not None:
            settings.summary_prompt = data.summary_prompt
        if data.metadata_targets is not None:
            settings.metadata_targets = data.metadata_targets
        if data.gpt_model is not None:
            settings.gpt_model = data.gpt_model
    else:
        settings = DatasetSettingsModel(
            dataset_id=dataset_id,
            chunk_size=data.chunk_size or 512,
            chunk_overlap=data.chunk_overlap or 50,
            summary_prompt=data.summary_prompt or "Сделай краткое резюме текста.",
            metadata_targets=data.metadata_targets or {},
            gpt_model=data.gpt_model or "gpt-3.5-turbo"
        )
        db.add(settings)

    await db.commit()
    return {"status": "ok"}
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from core.db import get_db
from core.security import get_current_user
from models.models import Link as LinkModel, Dataset
from api.schemas.links import LinkCreate, LinkUpdate, Link, LinkList, LinkState

router = APIRouter(prefix="/links", tags=["Links"])

@router.post("/", response_model=Link, status_code=status.HTTP_201_CREATED)
async def create_link(
    link: LinkCreate, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Проверка, что датасет существует и принадлежит пользователю
    result = await db.execute(
        select(Dataset).where(Dataset.id == link.dataset_id)
    )
    dataset = result.scalar_one_or_none()
    
    if not dataset or dataset.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found or does not belong to the current user"
        )
    
    # Создание новой ссылки
    db_link = LinkModel(
        url=link.url,
        dataset_id=link.dataset_id,
        state=LinkState.NEW
    )
    db.add(db_link)
    await db.flush()
    await db.refresh(db_link)
    return db_link

@router.get("/dataset/{dataset_id}", response_model=LinkList)
async def read_links_by_dataset(
    dataset_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Проверка, что датасет существует и принадлежит пользователю
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id)
    )
    dataset = result.scalar_one_or_none()
    
    if not dataset or dataset.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found or does not belong to the current user"
        )
    
    # Получение ссылок для датасета
    result = await db.execute(
        select(LinkModel)
        .where(LinkModel.dataset_id == dataset_id)
        .offset(skip)
        .limit(limit)
    )
    links = result.scalars().all()
    
    # Получение общего количества ссылок
    result = await db.execute(
        select(LinkModel.id)
        .where(LinkModel.dataset_id == dataset_id)
    )
    total = len(result.scalars().all())
    
    return {"links": links, "total": total}

@router.put("/{link_id}", response_model=Link)
async def update_link(
    link_id: int,
    link: LinkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Получение ссылки и проверка прав доступа
    result = await db.execute(
        select(LinkModel, Dataset)
        .join(Dataset, LinkModel.dataset_id == Dataset.id)
        .where(LinkModel.id == link_id)
    )
    db_result = result.first()
    
    if not db_result or db_result[1].user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found or does not belong to the current user"
        )
    
    db_link = db_result[0]
    
    # Обновление полей ссылки
    if link.url is not None:
        db_link.url = link.url
    if link.state is not None:
        db_link.state = link.state
    if link.error_message is not None:
        db_link.error_message = link.error_message
    
    await db.commit()
    await db.refresh(db_link)
    return db_link
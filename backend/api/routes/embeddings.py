from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from core.db import get_db
from core.security import get_current_user
from models.models import Embedding, Chunk
from api.schemas.embeddings import EmbeddingBase, EmbeddingCreate, EmbeddingResponse

router = APIRouter(prefix="/embeddings", tags=["Embeddings"])

@router.get("", response_model=List[EmbeddingResponse])
async def get_embeddings(
    chunk_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all embeddings with optional filtering by chunk_id
    """
    query = select(Embedding)
    
    if chunk_id:
        query = query.where(Embedding.chunk_id == chunk_id)
    
    # Add pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    embeddings = result.scalars().all()
    
    return embeddings

@router.get("/{chunk_id}", response_model=EmbeddingResponse)
async def get_embedding(
    chunk_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get a specific embedding by chunk_id
    """
    result = await db.execute(select(Embedding).where(Embedding.chunk_id == chunk_id))
    embedding = result.scalar_one_or_none()
    
    if not embedding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Embedding not found"
        )
    
    return embedding

@router.post("", response_model=EmbeddingResponse, status_code=status.HTTP_201_CREATED)
async def create_embedding(
    embedding: EmbeddingCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new embedding
    """
    # Verify that the chunk exists
    result = await db.execute(select(Chunk).where(Chunk.id == embedding.chunk_id))
    chunk = result.scalar_one_or_none()
    
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found"
        )
    
    # Check if embedding already exists
    result = await db.execute(select(Embedding).where(Embedding.chunk_id == embedding.chunk_id))
    existing_embedding = result.scalar_one_or_none()
    
    if existing_embedding:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Embedding already exists for this chunk"
        )
    
    # Create new embedding
    db_embedding = Embedding(**embedding.dict())
    db.add(db_embedding)
    await db.commit()
    await db.refresh(db_embedding)
    
    return db_embedding

@router.delete("/{chunk_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_embedding(
    chunk_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete an embedding
    """
    result = await db.execute(select(Embedding).where(Embedding.chunk_id == chunk_id))
    db_embedding = result.scalar_one_or_none()
    
    if not db_embedding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Embedding not found"
        )
    
    await db.delete(db_embedding)
    await db.commit()
    
    return None

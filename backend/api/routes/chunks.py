from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from core.db import get_db
from core.security import get_current_user
from models.models import Chunk, Page
from api.schemas.chunks import ChunkBase, ChunkCreate, ChunkUpdate, ChunkResponse

router = APIRouter(prefix="/chunks", tags=["Chunks"])

@router.get("", response_model=List[ChunkResponse])
async def get_chunks(
    page_id: Optional[int] = None,
    quality: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all chunks with optional filtering by page_id and quality
    """
    query = select(Chunk)
    
    if page_id:
        query = query.where(Chunk.page_id == page_id)
    
    if quality:
        query = query.where(Chunk.quality == quality)
    
    # Add pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    chunks = result.scalars().all()
    
    return chunks

@router.get("/{chunk_id}", response_model=ChunkResponse)
async def get_chunk(
    chunk_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get a specific chunk by ID
    """
    result = await db.execute(select(Chunk).where(Chunk.id == chunk_id))
    chunk = result.scalar_one_or_none()
    
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found"
        )
    
    return chunk

@router.post("", response_model=ChunkResponse, status_code=status.HTTP_201_CREATED)
async def create_chunk(
    chunk: ChunkCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new chunk
    """
    # Verify that the page exists
    result = await db.execute(select(Page).where(Page.id == chunk.page_id))
    page = result.scalar_one_or_none()
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found"
        )
    
    # Create new chunk
    db_chunk = Chunk(**chunk.dict())
    db.add(db_chunk)
    await db.commit()
    await db.refresh(db_chunk)
    
    return db_chunk

@router.put("/{chunk_id}", response_model=ChunkResponse)
async def update_chunk(
    chunk_id: int,
    chunk_update: ChunkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update an existing chunk
    """
    result = await db.execute(select(Chunk).where(Chunk.id == chunk_id))
    db_chunk = result.scalar_one_or_none()
    
    if not db_chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found"
        )
    
    # Update chunk attributes
    update_data = chunk_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_chunk, key, value)
    
    await db.commit()
    await db.refresh(db_chunk)
    
    return db_chunk

@router.delete("/{chunk_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chunk(
    chunk_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete a chunk
    """
    result = await db.execute(select(Chunk).where(Chunk.id == chunk_id))
    db_chunk = result.scalar_one_or_none()
    
    if not db_chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found"
        )
    
    await db.delete(db_chunk)
    await db.commit()
    
    return None

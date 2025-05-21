from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from core.db import get_db
from core.security import get_current_user
from models.models import Page, Link
from api.schemas.pages import PageBase, PageCreate, PageUpdate, PageResponse

router = APIRouter(prefix="/pages", tags=["Pages"])

@router.get("", response_model=List[PageResponse])
async def get_pages(
    link_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all pages with optional filtering by link_id
    """
    query = select(Page)
    
    if link_id:
        query = query.where(Page.link_id == link_id)
    
    # Add pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    pages = result.scalars().all()
    
    return pages

@router.get("/{page_id}", response_model=PageResponse)
async def get_page(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get a specific page by ID
    """
    result = await db.execute(select(Page).where(Page.id == page_id))
    page = result.scalar_one_or_none()
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found"
        )
    
    return page

@router.post("", response_model=PageResponse, status_code=status.HTTP_201_CREATED)
async def create_page(
    page: PageCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new page
    """
    # Verify that the link exists
    result = await db.execute(select(Link).where(Link.id == page.link_id))
    link = result.scalar_one_or_none()
    
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found"
        )
    
    # Create new page
    db_page = Page(**page.dict())
    db.add(db_page)
    await db.commit()
    await db.refresh(db_page)
    
    return db_page

@router.put("/{page_id}", response_model=PageResponse)
async def update_page(
    page_id: int,
    page_update: PageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update an existing page
    """
    result = await db.execute(select(Page).where(Page.id == page_id))
    db_page = result.scalar_one_or_none()
    
    if not db_page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found"
        )
    
    # Update page attributes
    update_data = page_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_page, key, value)
    
    await db.commit()
    await db.refresh(db_page)
    
    return db_page

@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_page(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete a page
    """
    result = await db.execute(select(Page).where(Page.id == page_id))
    db_page = result.scalar_one_or_none()
    
    if not db_page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found"
        )
    
    await db.delete(db_page)
    await db.commit()
    
    return None

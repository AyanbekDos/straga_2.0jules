from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class PageBase(BaseModel):
    url: str
    title: Optional[str] = None
    raw_html: str
    clean_text: Optional[str] = None
    raw_author: Optional[str] = None
    clean_author: Optional[str] = None
    author_needs_review: bool = False
    raw_date: Optional[str] = None
    clean_date: Optional[datetime] = None
    date_needs_review: bool = False
    raw_category: Optional[str] = None
    clean_category: Optional[str] = None
    category_needs_review: bool = False
    meta_data: Dict[str, Any] = Field(default_factory=dict)

class PageCreate(PageBase):
    link_id: int

class PageUpdate(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    raw_html: Optional[str] = None
    clean_text: Optional[str] = None
    raw_author: Optional[str] = None
    clean_author: Optional[str] = None
    author_needs_review: Optional[bool] = None
    raw_date: Optional[str] = None
    clean_date: Optional[datetime] = None
    date_needs_review: Optional[bool] = None
    raw_category: Optional[str] = None
    clean_category: Optional[str] = None
    category_needs_review: Optional[bool] = None
    meta_data: Optional[Dict[str, Any]] = None

class PageResponse(PageBase):
    id: int
    link_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

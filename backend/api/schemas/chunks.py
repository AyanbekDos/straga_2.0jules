from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class ChunkBase(BaseModel):
    chunk_index: int
    chunk_text: str
    summary: Optional[str] = None
    clean_author: Optional[str] = None
    chunk_meta_data: Dict[str, Any] = Field(default_factory=dict)
    quality: Optional[str] = None

class ChunkCreate(ChunkBase):
    page_id: int

class ChunkUpdate(BaseModel):
    chunk_index: Optional[int] = None
    chunk_text: Optional[str] = None
    summary: Optional[str] = None
    clean_author: Optional[str] = None
    chunk_meta_data: Optional[Dict[str, Any]] = None
    quality: Optional[str] = None

class ChunkResponse(ChunkBase):
    id: int
    page_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

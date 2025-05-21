from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class LinkState(str, Enum):
    NEW = "new"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"

class LinkBase(BaseModel):
    url: str
    dataset_id: int

class LinkCreate(LinkBase):
    pass

class LinkUpdate(BaseModel):
    url: Optional[str] = None
    state: Optional[LinkState] = None
    error_message: Optional[str] = None

class Link(LinkBase):
    id: int
    state: LinkState
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LinkList(BaseModel):
    links: List[Link]
    total: int
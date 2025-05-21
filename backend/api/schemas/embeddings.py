from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class EmbeddingBase(BaseModel):
    input: str
    vector: List[float]

class EmbeddingCreate(EmbeddingBase):
    chunk_id: int

class EmbeddingResponse(EmbeddingBase):
    chunk_id: int
    embed_at: datetime
    
    class Config:
        orm_mode = True

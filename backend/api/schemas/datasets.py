from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None

class DatasetCreate(DatasetBase):
    pass

class DatasetUpdate(DatasetBase):
    name: Optional[str] = None

class DatasetSettingsBase(BaseModel):
    chunk_size: int
    chunk_overlap: int
    summary_prompt: str
    gpt_model: str
    metadata_targets: Dict[str, Any]

class DatasetSettingsCreate(DatasetSettingsBase):
    pass

class DatasetSettingsUpdate(DatasetSettingsBase):
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    summary_prompt: Optional[str] = None
    gpt_model: Optional[str] = None
    metadata_targets: Optional[Dict[str, Any]] = None

class RecommendationResponse(BaseModel):
    meta_fields: List[dict]
    recommended_chunk_size: int
    recommended_chunk_overlap: int

class Dataset(DatasetBase):
    id: int
    user_id: int
    state: str
    error_count: int
    
    class Config:
        from_attributes = True
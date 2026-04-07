from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class SaveCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    snapshot: Dict[str, Any]  # 完整游戏状态


class SaveResponse(BaseModel):
    id: int
    campaign_id: int
    name: str
    description: Optional[str]
    snapshot: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class SessionLogResponse(BaseModel):
    id: int
    campaign_id: int
    session_number: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

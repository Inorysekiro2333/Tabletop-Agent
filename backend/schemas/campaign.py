from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from models.campaign import CampaignStatus


class CampaignCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    ai_config_id: Optional[int] = None
    system_prompt: Optional[str] = None


class CampaignUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    ai_config_id: Optional[int] = None
    system_prompt: Optional[str] = None
    current_session: Optional[int] = None
    status: Optional[CampaignStatus] = None


class CampaignResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    ai_config_id: Optional[int]
    system_prompt: Optional[str]
    current_session: int
    status: CampaignStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

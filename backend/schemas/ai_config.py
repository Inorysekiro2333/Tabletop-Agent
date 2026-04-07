from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from models.ai_config import AIProvider


class AIConfigCreate(BaseModel):
    provider: Literal["claude", "deepseek", "minimax"]
    api_key: str = Field(..., min_length=1)
    base_url: Optional[str] = None
    model_name: str = Field(..., min_length=1)


class AIConfigUpdate(BaseModel):
    provider: Optional[Literal["claude", "deepseek", "minimax"]] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    is_active: Optional[bool] = None


class AIConfigResponse(BaseModel):
    id: int
    user_id: int
    provider: AIProvider
    api_key_masked: str  # Return masked version
    base_url: Optional[str]
    model_name: str
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


def mask_api_key(api_key: str) -> str:
    """Mask API key for safe display"""
    if len(api_key) <= 8:
        return "****"
    return api_key[:4] + "****" + api_key[-4:]

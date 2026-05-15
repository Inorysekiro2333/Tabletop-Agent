from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime


class AttributesSchema(BaseModel):
    STR: int = Field(default=10, ge=1, le=30)
    DEX: int = Field(default=10, ge=1, le=30)
    CON: int = Field(default=10, ge=1, le=30)
    INT: int = Field(default=10, ge=1, le=30)
    WIS: int = Field(default=10, ge=1, le=30)
    CHA: int = Field(default=10, ge=1, le=30)


class PersonalitySchema(BaseModel):
    trait: Optional[str] = None
    ideal: Optional[str] = None
    bond: Optional[str] = None
    flaw: Optional[str] = None


class CharacterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    race: Optional[str] = None
    character_class: Optional[str] = None
    level: int = Field(default=1, ge=1, le=20)
    attributes: Optional[AttributesSchema] = None
    hp: int = Field(default=10, ge=1)
    ac: int = Field(default=10, ge=1)
    skills: Optional[List[str]] = []
    equipment: Optional[List[str]] = []
    backstory: Optional[str] = None
    personality: Optional[PersonalitySchema] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    race: Optional[str] = None
    character_class: Optional[str] = None
    level: Optional[int] = None
    attributes: Optional[AttributesSchema] = None
    hp: Optional[int] = None
    ac: Optional[int] = None
    skills: Optional[List[str]] = None
    equipment: Optional[List[str]] = None
    backstory: Optional[str] = None
    personality: Optional[PersonalitySchema] = None


class CharacterResponse(BaseModel):
    id: int
    user_id: int
    name: str
    race: Optional[str]
    character_class: Optional[str]
    level: int
    attributes: Dict[str, int]
    hp: int
    ac: int
    skills: List[str]
    equipment: Optional[List[str]] = []
    backstory: Optional[str]
    personality: Dict[str, str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CharacterGenerateRequest(BaseModel):
    """AI 生成角色卡的请求"""
    race_preference: Optional[str] = None  # e.g., "人类", "精灵", "矮人"
    class_preference: Optional[str] = None  # e.g., "战士", "法师", "盗贼"
    personality_hints: Optional[str] = None  # 性格提示

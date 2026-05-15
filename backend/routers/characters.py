from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.user import User
from models.character import Character
from models.ai_config import AIConfig
from schemas.character import (
    CharacterCreate,
    CharacterUpdate,
    CharacterResponse,
    CharacterGenerateRequest
)
from schemas.character import AttributesSchema, PersonalitySchema
from utils.security import get_current_user
from services.character_generator import generate_character

router = APIRouter(prefix="/characters", tags=["Characters"])


def character_to_response(char: Character) -> CharacterResponse:
    return CharacterResponse(
        id=char.id,
        user_id=char.user_id,
        name=char.name,
        race=char.race,
        character_class=char.character_class,
        level=char.level,
        attributes=char.attributes or {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
        hp=char.hp,
        ac=char.ac,
        skills=char.skills or [],
        equipment=char.equipment or [],
        backstory=char.backstory,
        personality=char.personality or {},
        created_at=char.created_at,
        updated_at=char.updated_at
    )


@router.get("", response_model=List[CharacterResponse])
async def list_characters(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all characters for current user"""
    characters = db.query(Character).filter(Character.user_id == current_user.id).all()
    return [character_to_response(c) for c in characters]


@router.post("", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def create_character(
    character_data: CharacterCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new character manually"""
    attributes_dict = character_data.attributes.model_dump() if character_data.attributes else None
    personality_dict = character_data.personality.model_dump() if character_data.personality else None

    character = Character(
        user_id=current_user.id,
        name=character_data.name,
        race=character_data.race,
        character_class=character_data.character_class,
        level=character_data.level,
        attributes=attributes_dict,
        hp=character_data.hp,
        ac=character_data.ac,
        skills=character_data.skills,
        equipment=character_data.equipment,
        backstory=character_data.backstory,
        personality=personality_dict
    )
    db.add(character)
    db.commit()
    db.refresh(character)

    return character_to_response(character)


@router.post("/generate", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def generate_character_api(
    request: CharacterGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a character using AI"""
    # 获取用户激活的 AI 配置
    ai_config = db.query(AIConfig).filter(
        AIConfig.user_id == current_user.id,
        AIConfig.is_active == True
    ).first()

    if not ai_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active AI configuration found. Please configure an AI first."
        )

    # 调用 AI 生成角色卡
    character_data = await generate_character(
        provider=ai_config.provider.value,
        api_key=ai_config.api_key,
        base_url=ai_config.base_url or "",
        model=ai_config.model_name,
        race_preference=request.race_preference,
        class_preference=request.class_preference,
        personality_hints=request.personality_hints
    )

    # 保存角色卡
    character = Character(
        user_id=current_user.id,
        name=character_data.get("name", "Unknown"),
        race=character_data.get("race"),
        character_class=character_data.get("class"),
        level=character_data.get("level", 1),
        attributes=character_data.get("attributes"),
        hp=character_data.get("hp", 10),
        ac=character_data.get("ac", 10),
        skills=character_data.get("skills", []),
        backstory=character_data.get("backstory"),
        personality=character_data.get("personality")
    )
    db.add(character)
    db.commit()
    db.refresh(character)

    return character_to_response(character)


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific character"""
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id
    ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    return character_to_response(character)


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: int,
    character_data: CharacterUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a character"""
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id
    ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    update_data = character_data.model_dump(exclude_unset=True)

    # 处理嵌套对象
    if "attributes" in update_data and update_data["attributes"]:
        update_data["attributes"] = character_data.attributes.model_dump()
    if "personality" in update_data and update_data["personality"]:
        update_data["personality"] = character_data.personality.model_dump()

    for field, value in update_data.items():
        setattr(character, field, value)

    db.commit()
    db.refresh(character)

    return character_to_response(character)


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
    character_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a character"""
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id
    ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    db.delete(character)
    db.commit()

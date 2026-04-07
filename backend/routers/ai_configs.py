from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.user import User
from models.ai_config import AIConfig
from schemas.ai_config import (
    AIConfigCreate,
    AIConfigUpdate,
    AIConfigResponse,
    mask_api_key
)
from utils.security import get_current_user

router = APIRouter(prefix="/ai-configs", tags=["AI Configuration"])
from config import get_settings
settings = get_settings()


@router.get("", response_model=List[AIConfigResponse])
async def list_ai_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all AI configurations for current user"""
    configs = db.query(AIConfig).filter(AIConfig.user_id == current_user.id).all()
    return [
        AIConfigResponse(
            id=c.id,
            user_id=c.user_id,
            provider=c.provider,
            api_key_masked=mask_api_key(c.api_key),
            base_url=c.base_url,
            model_name=c.model_name,
            is_active=c.is_active,
            created_at=c.created_at
        )
        for c in configs
    ]


@router.post("", response_model=AIConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_config(
    config_data: AIConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new AI configuration"""
    config = AIConfig(
        user_id=current_user.id,
        provider=config_data.provider,
        api_key=config_data.api_key,
        base_url=config_data.base_url,
        model_name=config_data.model_name
    )
    db.add(config)
    db.commit()
    db.refresh(config)

    return AIConfigResponse(
        id=config.id,
        user_id=config.user_id,
        provider=config.provider,
        api_key_masked=mask_api_key(config.api_key),
        base_url=config.base_url,
        model_name=config.model_name,
        is_active=config.is_active,
        created_at=config.created_at
    )


@router.get("/{config_id}", response_model=AIConfigResponse)
async def get_ai_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific AI configuration"""
    config = db.query(AIConfig).filter(
        AIConfig.id == config_id,
        AIConfig.user_id == current_user.id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found"
        )

    return AIConfigResponse(
        id=config.id,
        user_id=config.user_id,
        provider=config.provider,
        api_key_masked=mask_api_key(config.api_key),
        base_url=config.base_url,
        model_name=config.model_name,
        is_active=config.is_active,
        created_at=config.created_at
    )


@router.put("/{config_id}", response_model=AIConfigResponse)
async def update_ai_config(
    config_id: int,
    config_data: AIConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an AI configuration"""
    config = db.query(AIConfig).filter(
        AIConfig.id == config_id,
        AIConfig.user_id == current_user.id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found"
        )

    update_data = config_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)

    return AIConfigResponse(
        id=config.id,
        user_id=config.user_id,
        provider=config.provider,
        api_key_masked=mask_api_key(config.api_key),
        base_url=config.base_url,
        model_name=config.model_name,
        is_active=config.is_active,
        created_at=config.created_at
    )


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an AI configuration"""
    config = db.query(AIConfig).filter(
        AIConfig.id == config_id,
        AIConfig.user_id == current_user.id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found"
        )

    db.delete(config)
    db.commit()


@router.put("/{config_id}/activate", response_model=AIConfigResponse)
async def activate_ai_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set an AI configuration as the active/default one"""
    # Deactivate all other configs for this user
    db.query(AIConfig).filter(AIConfig.user_id == current_user.id).update(
        {"is_active": False}
    )

    # Activate the specified config
    config = db.query(AIConfig).filter(
        AIConfig.id == config_id,
        AIConfig.user_id == current_user.id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found"
        )

    config.is_active = True
    db.commit()
    db.refresh(config)

    return AIConfigResponse(
        id=config.id,
        user_id=config.user_id,
        provider=config.provider,
        api_key_masked=mask_api_key(config.api_key),
        base_url=config.base_url,
        model_name=config.model_name,
        is_active=config.is_active,
        created_at=config.created_at
    )

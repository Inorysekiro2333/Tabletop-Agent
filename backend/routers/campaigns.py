from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.user import User
from models.campaign import Campaign, CampaignStatus
from models.ai_config import AIConfig
from schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse
from utils.security import get_current_user

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all campaigns for current user"""
    campaigns = db.query(Campaign).filter(Campaign.user_id == current_user.id).all()
    return campaigns


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new campaign"""
    # 验证 AI 配置存在且属于当前用户
    if campaign_data.ai_config_id:
        ai_config = db.query(AIConfig).filter(
            AIConfig.id == campaign_data.ai_config_id,
            AIConfig.user_id == current_user.id
        ).first()
        if not ai_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AI configuration not found"
            )

    campaign = Campaign(
        user_id=current_user.id,
        title=campaign_data.title,
        description=campaign_data.description,
        ai_config_id=campaign_data.ai_config_id,
        system_prompt=campaign_data.system_prompt
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific campaign"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    return campaign


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    campaign_data: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a campaign"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    # 验证 AI 配置
    if campaign_data.ai_config_id:
        ai_config = db.query(AIConfig).filter(
            AIConfig.id == campaign_data.ai_config_id,
            AIConfig.user_id == current_user.id
        ).first()
        if not ai_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AI configuration not found"
            )

    update_data = campaign_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campaign, field, value)

    db.commit()
    db.refresh(campaign)

    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a campaign"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    db.delete(campaign)
    db.commit()

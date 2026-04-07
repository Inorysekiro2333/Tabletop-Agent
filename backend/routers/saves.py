from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.user import User
from models.campaign import Campaign
from models.save import Save, SessionLog
from schemas.save import SaveCreate, SaveResponse, SessionLogResponse
from utils.security import get_current_user

router = APIRouter(prefix="/saves", tags=["Saves"])


def verify_campaign_access(campaign_id: int, user_id: int, db: Session) -> Campaign:
    """验证用户对战役的访问权限"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == user_id
    ).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    return campaign


@router.get("/campaign/{campaign_id}/saves", response_model=List[SaveResponse])
async def list_saves(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all saves for a campaign"""
    verify_campaign_access(campaign_id, current_user.id, db)
    saves = db.query(Save).filter(Save.campaign_id == campaign_id).order_by(Save.created_at.desc()).all()
    return saves


@router.post("/campaign/{campaign_id}/saves", response_model=SaveResponse, status_code=status.HTTP_201_CREATED)
async def create_save(
    campaign_id: int,
    save_data: SaveCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new save for a campaign"""
    verify_campaign_access(campaign_id, current_user.id, db)

    save = Save(
        campaign_id=campaign_id,
        name=save_data.name,
        description=save_data.description,
        snapshot=save_data.snapshot
    )
    db.add(save)
    db.commit()
    db.refresh(save)

    return save


@router.post("/saves/{save_id}/load", response_model=SaveResponse)
async def load_save(
    save_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Load a save (returns the snapshot data)"""
    save = db.query(Save).filter(Save.id == save_id).first()
    if not save:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Save not found"
        )

    # 验证访问权限
    verify_campaign_access(save.campaign_id, current_user.id, db)

    return save


@router.delete("/saves/{save_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_save(
    save_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a save"""
    save = db.query(Save).filter(Save.id == save_id).first()
    if not save:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Save not found"
        )

    # 验证访问权限
    verify_campaign_access(save.campaign_id, current_user.id, db)

    db.delete(save)
    db.commit()


# Session Logs
@router.get("/campaign/{campaign_id}/logs", response_model=List[SessionLogResponse])
async def list_session_logs(
    campaign_id: int,
    session_number: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List session logs for a campaign"""
    verify_campaign_access(campaign_id, current_user.id, db)

    query = db.query(SessionLog).filter(SessionLog.campaign_id == campaign_id)
    if session_number:
        query = query.filter(SessionLog.session_number == session_number)

    logs = query.order_by(SessionLog.created_at.asc()).all()
    return logs


@router.post("/campaign/{campaign_id}/logs", status_code=status.HTTP_201_CREATED)
async def create_session_log(
    campaign_id: int,
    role: str,
    content: str,
    session_number: int = 1,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a session log entry"""
    verify_campaign_access(campaign_id, current_user.id, db)

    log = SessionLog(
        campaign_id=campaign_id,
        session_number=session_number,
        role=role,
        content=content
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return log

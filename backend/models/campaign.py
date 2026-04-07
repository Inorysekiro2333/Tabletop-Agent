from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import func
import enum


class CampaignStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    ai_config_id = Column(Integer, ForeignKey("ai_configs.id"), nullable=True)
    system_prompt = Column(Text, nullable=True)
    current_session = Column(Integer, default=1)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.ACTIVE)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="campaigns")
    ai_config = relationship("AIConfig", backref="campaigns")

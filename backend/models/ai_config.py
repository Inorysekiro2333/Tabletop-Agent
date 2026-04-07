from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import func
import enum


class AIProvider(str, enum.Enum):
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"
    MINIMAX = "minimax"


class AIConfig(Base):
    __tablename__ = "ai_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(SQLEnum(AIProvider), nullable=False)
    api_key = Column(String(500), nullable=False)
    base_url = Column(String(255), nullable=True)
    model_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", backref="ai_configs")

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import func


class Save(Base):
    __tablename__ = "saves"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    snapshot = Column(JSON, nullable=False)  # 完整游戏状态
    created_at = Column(DateTime, server_default=func.now())

    campaign = relationship("Campaign", backref="saves")


class SessionLog(Base):
    __tablename__ = "session_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    session_number = Column(Integer, nullable=False, default=1)
    role = Column(String(20), nullable=False)  # 'player', 'kp', 'npc', 'ai_companion', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    campaign = relationship("Campaign", backref="session_logs")

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import func


class ChatBranch(Base):
    __tablename__ = "chat_branches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    parent_message_id = Column(Integer, nullable=True)  # Fork point in SessionLog
    name = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    campaign = relationship("Campaign", backref="chat_branches")

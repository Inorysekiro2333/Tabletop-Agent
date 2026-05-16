from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import func


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    race = Column(String(50), nullable=True)
    character_class = Column(String(50), nullable=True)
    level = Column(Integer, default=1)
    attributes = Column(JSON, default=dict)  # STR, DEX, CON, INT, WIS, CHA
    hp = Column(Integer, default=10)
    ac = Column(Integer, default=10)
    skills = Column(JSON, default=list)  # 技能列表
    equipment = Column(JSON, default=list)  # 装备/背包物品列表
    backstory = Column(Text, nullable=True)
    personality = Column(JSON, default=dict)  # trait, ideal, bond, flaw
    relationships = Column(JSON, default=list)  # [{name, type, description, attitude}]
    faction = Column(String(100), nullable=True)  # 阵营/派系
    goals = Column(JSON, default=list)  # [{name, description, status}]
    ideals = Column(JSON, default=list)  # 理想/信念
    flaws = Column(JSON, default=list)  # 性格缺陷
    personal_traits = Column(JSON, default=list)  # 个人特质
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="characters")

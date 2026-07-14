import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Text, ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship
from .database import Base

import enum


def gen_id():
    return str(uuid.uuid4())


class SentimentEnum(str, enum.Enum):
    positive = "Positive"
    neutral = "Neutral"
    negative = "Negative"


class HCP(Base):
    """A Healthcare Professional the field rep interacts with."""
    __tablename__ = "hcps"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=True)
    hospital = Column(String, nullable=True)

    interactions = relationship("Interaction", back_populates="hcp")


class Interaction(Base):
    """A single logged HCP interaction. This row backs the left-hand form."""
    __tablename__ = "interactions"

    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String, index=True, nullable=False)

    hcp_id = Column(String, ForeignKey("hcps.id"), nullable=True)
    hcp_name = Column(String, nullable=True)  # denormalized for free-text entry before HCP is matched

    interaction_type = Column(String, nullable=True)  # Meeting / Call / Email / Conference
    date = Column(String, nullable=True)   # stored as free text (DD-MM-YYYY) to mirror the mock
    time = Column(String, nullable=True)

    attendees = Column(Text, nullable=True)
    topics_discussed = Column(Text, nullable=True)

    materials_shared = Column(JSON, default=list)   # list[str]
    samples_distributed = Column(JSON, default=list)  # list[str]

    sentiment = Column(Enum(SentimentEnum), nullable=True)

    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)
    ai_suggested_followups = Column(JSON, default=list)  # list[str]

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")


class ChatMessage(Base):
    """Chat transcript per session, used to give the LangGraph agent memory."""
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)  # user | assistant | tool
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
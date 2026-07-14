from typing import Optional, List
from pydantic import BaseModel


class InteractionState(BaseModel):
    """This is the exact shape of the left-hand form. The frontend renders
    directly off this object and the agent's tools are the only thing
    allowed to change it."""
    id: Optional[str] = None
    hcp_name: Optional[str] = None
    interaction_type: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    materials_shared: List[str] = []
    samples_distributed: List[str] = []
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    ai_suggested_followups: List[str] = []

    class Config:
        from_attributes = True


class InteractionUpdate(BaseModel):
    """Partial update payload for direct form edits (manual entry path,
    separate from the chat/agent path but writing to the same record)."""
    hcp_name: Optional[str] = None
    interaction_type: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[List[str]] = None
    samples_distributed: Optional[List[str]] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ToolCallLog(BaseModel):
    tool: str
    args: dict
    result_summary: str


class ChatResponse(BaseModel):
    reply: str
    form_state: InteractionState
    tool_calls: List[ToolCallLog] = []


class HCPOut(BaseModel):
    id: str
    name: str
    specialty: Optional[str] = None
    hospital: Optional[str] = None

    class Config:
        from_attributes = True
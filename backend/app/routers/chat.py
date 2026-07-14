from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage

from .. import models, schemas
from ..database import get_db
from ..agent.tools import build_tools, ToolCallRecorder, _get_or_create_interaction, _serialize
from ..agent.graph import build_graph

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=schemas.ChatResponse)
def chat(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    recorder = ToolCallRecorder()
    tools = build_tools(db, payload.session_id, recorder)
    graph = build_graph(tools)

    # Rehydrate short conversation history so the agent has memory of
    # earlier turns in this session (needed for multi-turn corrections).
    history = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == payload.session_id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )
    messages = []
    for m in history[-20:]:
        if m.role == "user":
            messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            messages.append(AIMessage(content=m.content))
    messages.append(HumanMessage(content=payload.message))

    # persist the incoming user message
    db.add(models.ChatMessage(session_id=payload.session_id, role="user", content=payload.message))
    db.commit()

    result = graph.invoke({"messages": messages, "session_id": payload.session_id})
    final_message = result["messages"][-1]
    reply_text = final_message.content or "Got it."

    db.add(models.ChatMessage(session_id=payload.session_id, role="assistant", content=reply_text))
    db.commit()

    interaction = _get_or_create_interaction(db, payload.session_id)
    form_state = _serialize(interaction)
    form_state["id"] = interaction.id

    return schemas.ChatResponse(
        reply=reply_text,
        form_state=schemas.InteractionState(**form_state),
        tool_calls=[schemas.ToolCallLog(**c) for c in recorder.calls],
    )

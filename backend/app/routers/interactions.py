from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.get("/{session_id}/current", response_model=schemas.InteractionState)
def get_current(session_id: str, db: Session = Depends(get_db)):
    interaction = (
        db.query(models.Interaction)
        .filter(models.Interaction.session_id == session_id)
        .order_by(models.Interaction.created_at.desc())
        .first()
    )
    if interaction is None:
        return schemas.InteractionState()
    return schemas.InteractionState(
        id=interaction.id,
        hcp_name=interaction.hcp_name,
        interaction_type=interaction.interaction_type,
        date=interaction.date,
        time=interaction.time,
        attendees=interaction.attendees,
        topics_discussed=interaction.topics_discussed,
        materials_shared=interaction.materials_shared or [],
        samples_distributed=interaction.samples_distributed or [],
        sentiment=interaction.sentiment.value if interaction.sentiment else None,
        outcomes=interaction.outcomes,
        follow_up_actions=interaction.follow_up_actions,
        ai_suggested_followups=interaction.ai_suggested_followups or [],
    )


@router.patch("/{session_id}/fields", response_model=schemas.InteractionState)
def update_fields(session_id: str, payload: schemas.InteractionUpdate, db: Session = Depends(get_db)):
    """Direct manual edit path -- used when the rep types into the form
    itself instead of describing the visit in chat. Writes to the exact
    same Interaction row the chat/agent path uses, so both entry methods
    stay perfectly consistent."""
    interaction = (
        db.query(models.Interaction)
        .filter(models.Interaction.session_id == session_id)
        .order_by(models.Interaction.created_at.desc())
        .first()
    )
    if interaction is None:
        interaction = models.Interaction(session_id=session_id)
        db.add(interaction)
        db.commit()
        db.refresh(interaction)

    data = payload.model_dump(exclude_unset=True)

    if "sentiment" in data and data["sentiment"] is not None:
        sentiment_norm = data["sentiment"].strip().capitalize()
        if sentiment_norm in ("Positive", "Neutral", "Negative"):
            interaction.sentiment = models.SentimentEnum(sentiment_norm)
        data.pop("sentiment")

    for field, value in data.items():
        setattr(interaction, field, value)

    db.commit()
    db.refresh(interaction)

    return schemas.InteractionState(
        id=interaction.id,
        hcp_name=interaction.hcp_name,
        interaction_type=interaction.interaction_type,
        date=interaction.date,
        time=interaction.time,
        attendees=interaction.attendees,
        topics_discussed=interaction.topics_discussed,
        materials_shared=interaction.materials_shared or [],
        samples_distributed=interaction.samples_distributed or [],
        sentiment=interaction.sentiment.value if interaction.sentiment else None,
        outcomes=interaction.outcomes,
        follow_up_actions=interaction.follow_up_actions,
        ai_suggested_followups=interaction.ai_suggested_followups or [],
    )


@router.post("/{session_id}/new")
def start_new(session_id: str, db: Session = Depends(get_db)):
    """Explicitly start a fresh interaction record (new visit) for a session."""
    interaction = models.Interaction(session_id=session_id)
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return {"id": interaction.id}
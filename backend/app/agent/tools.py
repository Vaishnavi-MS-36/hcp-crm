"""
LangGraph tools for the HCP CRM agent.

Every tool here is a real write path into the `interactions` table. The LLM
is bound to these tools and decides (a) which tool to call and (b) what
arguments to extract from the rep's natural-language message. The tool
functions themselves never guess -- they just persist exactly what the LLM
extracted and return a fresh snapshot of the form, which is what keeps the
left-hand "Interaction Details" panel truthful.

Mandatory tools (per assignment spec):
  1. log_interaction   - create/populate the interaction from free text
  2. edit_interaction  - modify specific fields of the existing interaction

Additional tools we defined ourselves:
  3. search_or_create_hcp   - resolves "HCP Name" against the HCP directory
  4. log_material_or_sample - adds materials/samples incrementally
  5. suggest_followups      - AI-generated next-step suggestions
"""
from typing import List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models


# A mutable box so tool functions (which must match the @tool signature,
# no extra positional args) can still report what happened back up to the
# API layer for the `tool_calls` field in the response / for logging.
class ToolCallRecorder:
    def __init__(self):
        self.calls = []

    def record(self, tool_name: str, args: dict, summary: str):
        self.calls.append({"tool": tool_name, "args": args, "result_summary": summary})


def _get_or_create_interaction(db: Session, session_id: str) -> models.Interaction:
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
    return interaction


def _serialize(interaction: models.Interaction) -> dict:
    return {
        "id": interaction.id,
        "hcp_name": interaction.hcp_name,
        "interaction_type": interaction.interaction_type,
        "date": interaction.date,
        "time": interaction.time,
        "attendees": interaction.attendees,
        "topics_discussed": interaction.topics_discussed,
        "materials_shared": interaction.materials_shared or [],
        "samples_distributed": interaction.samples_distributed or [],
        "sentiment": interaction.sentiment.value if interaction.sentiment else None,
        "outcomes": interaction.outcomes,
        "follow_up_actions": interaction.follow_up_actions,
        "ai_suggested_followups": interaction.ai_suggested_followups or [],
    }


def build_tools(db: Session, session_id: str, recorder: ToolCallRecorder):
    """Build the 5 tools bound to a specific DB session + chat session.

    Binding via closure (instead of passing db/session_id as LLM-visible
    args) is deliberate: the LLM should only ever choose *business* fields,
    never infrastructure identifiers.
    """

    # ---------------------------------------------------------------
    # 1. MANDATORY: Log Interaction
    # ---------------------------------------------------------------
    class LogInteractionArgs(BaseModel):
        hcp_name: Optional[str] = Field(None, description="Name of the HCP the rep met, e.g. 'Dr. Smith'")
        interaction_type: Optional[str] = Field(None, description="One of: Meeting, Call, Email, Conference")
        date: Optional[str] = Field(None, description="Date of the interaction, format DD-MM-YYYY")
        time: Optional[str] = Field(None, description="Time of the interaction, e.g. '14:30'")
        attendees: Optional[str] = Field(None, description="Comma separated names of anyone else present")
        topics_discussed: Optional[str] = Field(None, description="Summary of what was discussed, e.g. product efficacy, safety data")
        materials_shared: Optional[List[str]] = Field(None, description="Marketing materials/brochures shared")
        samples_distributed: Optional[List[str]] = Field(None, description="Drug samples given to the HCP")
        sentiment: Optional[str] = Field(None, description="Observed HCP sentiment: Positive, Neutral, or Negative")
        outcomes: Optional[str] = Field(None, description="Key outcomes or agreements reached")
        follow_up_actions: Optional[str] = Field(None, description="Concrete next steps the rep committed to")

    @tool("log_interaction", args_schema=LogInteractionArgs)
    def log_interaction(
        hcp_name: Optional[str] = None,
        interaction_type: Optional[str] = None,
        date: Optional[str] = None,
        time: Optional[str] = None,
        attendees: Optional[str] = None,
        topics_discussed: Optional[str] = None,
        materials_shared: Optional[List[str]] = None,
        samples_distributed: Optional[List[str]] = None,
        sentiment: Optional[str] = None,
        outcomes: Optional[str] = None,
        follow_up_actions: Optional[str] = None,
    ) -> dict:
        """Create or populate the HCP interaction record from a natural
        language description of a rep/HCP meeting. Call this the first time
        an interaction is described. Extract every field you can find in
        the rep's message; leave anything not mentioned as null so it
        doesn't overwrite existing data."""
        interaction = _get_or_create_interaction(db, session_id)

        updates = {
            "hcp_name": hcp_name,
            "interaction_type": interaction_type,
            "date": date,
            "time": time,
            "attendees": attendees,
            "topics_discussed": topics_discussed,
            "outcomes": outcomes,
            "follow_up_actions": follow_up_actions,
        }
        for field, value in updates.items():
            if value is not None:
                setattr(interaction, field, value)

        if materials_shared:
            interaction.materials_shared = list({*(interaction.materials_shared or []), *materials_shared})
        if samples_distributed:
            interaction.samples_distributed = list({*(interaction.samples_distributed or []), *samples_distributed})
        if sentiment:
            sentiment_norm = sentiment.strip().capitalize()
            if sentiment_norm in ("Positive", "Neutral", "Negative"):
                interaction.sentiment = models.SentimentEnum(sentiment_norm)

        db.commit()
        db.refresh(interaction)

        changed = {k: v for k, v in updates.items() if v is not None}
        summary = f"Logged interaction fields: {', '.join(changed.keys()) or 'no new fields'}"
        recorder.record("log_interaction", {k: v for k, v in locals().items() if k in LogInteractionArgs.model_fields}, summary)
        return _serialize(interaction)

    # ---------------------------------------------------------------
    # 2. MANDATORY: Edit Interaction
    # ---------------------------------------------------------------
    class EditInteractionArgs(BaseModel):
        field: str = Field(..., description=(
            "Exact field to change. One of: hcp_name, interaction_type, date, time, "
            "attendees, topics_discussed, sentiment, outcomes, follow_up_actions"
        ))
        new_value: str = Field(..., description="The corrected/updated value for that field")

    @tool("edit_interaction", args_schema=EditInteractionArgs)
    def edit_interaction(field: str, new_value: str) -> dict:
        """Modify exactly one field of the ALREADY-LOGGED interaction, e.g.
        'actually change the date to the 22nd' or 'sentiment was actually
        positive'. Never touches any field other than the one named. Use
        log_interaction instead if no interaction exists yet."""
        interaction = _get_or_create_interaction(db, session_id)

        allowed_fields = {
            "hcp_name", "interaction_type", "date", "time", "attendees",
            "topics_discussed", "sentiment", "outcomes", "follow_up_actions",
        }
        if field not in allowed_fields:
            summary = f"Rejected edit: unknown field '{field}'"
            recorder.record("edit_interaction", {"field": field, "new_value": new_value}, summary)
            return _serialize(interaction)

        if field == "sentiment":
            sentiment_norm = new_value.strip().capitalize()
            if sentiment_norm in ("Positive", "Neutral", "Negative"):
                interaction.sentiment = models.SentimentEnum(sentiment_norm)
        else:
            setattr(interaction, field, new_value)

        db.commit()
        db.refresh(interaction)

        summary = f"Edited '{field}' -> '{new_value}'"
        recorder.record("edit_interaction", {"field": field, "new_value": new_value}, summary)
        return _serialize(interaction)

    # ---------------------------------------------------------------
    # 3. Search / create HCP (directory resolution)
    # ---------------------------------------------------------------
    class SearchHCPArgs(BaseModel):
        name: str = Field(..., description="HCP name to search for or register, e.g. 'Dr. Priya Sharma'")
        specialty: Optional[str] = Field(None, description="Medical specialty, if mentioned")
        hospital: Optional[str] = Field(None, description="Hospital/clinic, if mentioned")

    @tool("search_or_create_hcp", args_schema=SearchHCPArgs)
    def search_or_create_hcp(name: str, specialty: Optional[str] = None, hospital: Optional[str] = None) -> dict:
        """Look up an HCP by name in the CRM directory (fuzzy, case
        insensitive). If no match exists, register a new HCP record. Also
        links the resolved HCP to the current interaction. Use this when
        the rep names a doctor so the form's HCP field is backed by a real
        directory entry rather than free text."""
        existing = (
            db.query(models.HCP)
            .filter(models.HCP.name.ilike(f"%{name.strip()}%"))
            .first()
        )
        if existing is None:
            existing = models.HCP(name=name, specialty=specialty, hospital=hospital)
            db.add(existing)
            db.commit()
            db.refresh(existing)
            summary = f"Registered new HCP '{name}'"
        else:
            summary = f"Matched existing HCP '{existing.name}'"

        interaction = _get_or_create_interaction(db, session_id)
        interaction.hcp_id = existing.id
        interaction.hcp_name = existing.name
        db.commit()
        db.refresh(interaction)

        recorder.record("search_or_create_hcp", {"name": name, "specialty": specialty, "hospital": hospital}, summary)
        return _serialize(interaction)

    # ---------------------------------------------------------------
    # 4. Log material or sample (incremental additions)
    # ---------------------------------------------------------------
    class MaterialSampleArgs(BaseModel):
        materials: Optional[List[str]] = Field(None, description="Marketing/brochure materials to add, e.g. ['OncoBoost Phase III PDF']")
        samples: Optional[List[str]] = Field(None, description="Drug samples to add, e.g. ['OncoBoost 50mg x10']")

    @tool("log_material_or_sample", args_schema=MaterialSampleArgs)
    def log_material_or_sample(materials: Optional[List[str]] = None, samples: Optional[List[str]] = None) -> dict:
        """Add one or more materials shared and/or samples distributed to
        the current interaction, without touching any other field. Use
        this for follow-up mentions like 'also left a brochure' after the
        main interaction has already been logged."""
        interaction = _get_or_create_interaction(db, session_id)
        if materials:
            interaction.materials_shared = list({*(interaction.materials_shared or []), *materials})
        if samples:
            interaction.samples_distributed = list({*(interaction.samples_distributed or []), *samples})
        db.commit()
        db.refresh(interaction)

        summary = f"Added materials={materials or []} samples={samples or []}"
        recorder.record("log_material_or_sample", {"materials": materials, "samples": samples}, summary)
        return _serialize(interaction)

    # ---------------------------------------------------------------
    # 5. Suggest follow-ups
    # ---------------------------------------------------------------
    class SuggestFollowupsArgs(BaseModel):
        suggestions: List[str] = Field(..., description=(
            "2-4 concrete, specific next-step suggestions grounded in the "
            "logged topics/outcomes, e.g. 'Schedule follow-up meeting in 2 weeks'"
        ))

    @tool("suggest_followups", args_schema=SuggestFollowupsArgs)
    def suggest_followups(suggestions: List[str]) -> dict:
        """Populate the 'AI Suggested Follow-ups' panel with concrete next
        steps derived from the topics discussed and outcomes already
        logged for this interaction. Call this after log_interaction has
        captured enough context (topics/outcomes) to ground real
        suggestions -- don't invent suggestions unrelated to the
        conversation."""
        interaction = _get_or_create_interaction(db, session_id)
        interaction.ai_suggested_followups = list(suggestions)
        db.commit()
        db.refresh(interaction)

        summary = f"Suggested {len(suggestions)} follow-up(s)"
        recorder.record("suggest_followups", {"suggestions": suggestions}, summary)
        return _serialize(interaction)

    return [
        log_interaction,
        edit_interaction,
        search_or_create_hcp,
        log_material_or_sample,
        suggest_followups,
    ]

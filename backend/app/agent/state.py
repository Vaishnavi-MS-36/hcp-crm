from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State threaded through the LangGraph graph for one /chat turn.

    `messages` is the running conversation (human, ai, tool messages) that
    LangGraph's prebuilt `add_messages` reducer appends to. The agent never
    stores the CRM form fields in here -- that would let the LLM "imagine"
    field values without actually calling a tool. Instead, every field
    mutation must go through a tool call that writes to the database, which
    keeps the left-hand form perfectly in sync with what the agent actually
    did (not just what it said).
    """
    messages: Annotated[list, add_messages]
    session_id: str

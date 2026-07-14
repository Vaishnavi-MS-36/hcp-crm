"""
Builds the LangGraph StateGraph that powers the AI Assistant panel.

Role of the LangGraph agent (see assignment: "Describe the role of the
LangGraph agent in managing HCP interactions"):

    The agent is the *only* actor allowed to mutate the Interaction record
    that the left-hand form renders. On every chat turn it:
      1. Reads the running conversation (`agent` node) and decides, using
         the Groq LLM, whether the rep's message requires calling one or
         more of the 5 tools (create/edit the interaction, resolve the HCP,
         log materials/samples, or suggest follow-ups).
      2. If it does, LangGraph routes to the `tools` node, which executes
         the real database writes and returns each tool's result as a
         ToolMessage.
      3. The graph loops back to `agent` so the LLM can see the tool
         results and either call another tool (e.g. log_interaction then
         suggest_followups) or produce a final natural-language reply.
      4. Once the LLM responds with no further tool calls, the graph ends
         and the API layer reads the latest Interaction row back out of
         the database to refresh the form the user sees.

    This keeps the chat UI and the structured form perfectly consistent:
    the form only ever reflects what a tool actually persisted, never what
    the LLM merely "said" it did.
"""
import os
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

from .state import AgentState

SYSTEM_PROMPT = """You are the AI Assistant embedded in a pharma CRM's HCP \
Interaction Log screen. Field reps describe their visits to doctors in \
plain English (or ask you to fix something they already logged), and you \
are the ONLY way the structured form on the left gets filled in -- the rep \
cannot type into it directly.

Rules:
- If the rep describes a new interaction (who they met, what was \
discussed, samples/materials, sentiment, outcomes, next steps), call \
`search_or_create_hcp` first if a doctor's name is mentioned, then call \
`log_interaction` with every field you can extract.
- After an interaction has topics/outcomes logged, call `suggest_followups` \
with 2-4 concrete suggestions grounded in what was actually discussed.
- If the rep corrects or changes ONE existing field ("actually it was \
neutral", "change the date to..."), call `edit_interaction` -- never \
re-call log_interaction for a single-field correction.
- If the rep separately mentions materials or samples after the main log, \
use `log_material_or_sample`.
- Never fabricate information the rep didn't say. Leave fields null/empty \
if unmentioned.
- After tool calls settle, reply to the rep in one short, friendly \
sentence confirming what you logged. Do not repeat the raw form back as a \
wall of text -- the rep can already see the form."""


def get_llm(model: str = None):
    return ChatGroq(
        model=model or os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2,
    )


def build_graph(tools):
    llm = get_llm().bind_tools(tools)

    def agent_node(state: AgentState):
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]
        response = llm.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState):
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    tool_node = ToolNode(tools)

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()

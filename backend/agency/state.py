from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """The state of the PaperPilot agentic flow."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    market_context: dict
    trade_proposal: dict
    risk_shield_status: str # "SAFE", "SHIELD_ACTIVE", "CRISIS"
    decision_reasoning: str

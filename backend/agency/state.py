from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import NotRequired

class MarketContext(TypedDict):
    equity: float
    vix_close: float
    latest_prices: dict[str, float]
    dry_run: NotRequired[bool]
    epsilon: NotRequired[float]
    risk_override: NotRequired[str | None]
    sentiment: NotRequired[float]

class AgentState(TypedDict):
    """The state of the PaperPilot agentic flow."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    market_context: MarketContext
    trade_proposal: dict
    risk_shield_status: str # "SAFE", "SHIELD_ACTIVE", "CRISIS"
    decision_reasoning: str

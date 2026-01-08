import logging
from typing import Literal
from langgraph.graph import StateGraph, END
from backend.agency.state import AgentState
from backend.agency.sentinel import SentinelShield
from backend.learning import EpsilonGreedyBandit
from backend.db import SessionLocal
from backend.config import TRADED_SYMBOLS

logger = logging.getLogger("AgentGraph")

# --- Nodes ---

async def sentinel_node(state: AgentState):
    """Checks VIX and Sentiment to determine if it's safe to trade."""
    sentinel = SentinelShield()
    
    # 1. Regime Analysis
    vix = state["market_context"].get("vix_close", 20.0)
    regime = sentinel.analyze_vix_regime(vix)
    
    # 2. Sentiment Analysis
    sentiment_score = await sentinel.analyze_sentiment(TRADED_SYMBOLS[:3]) # Just top 3 for speed
    
    status = regime
    if sentiment_score < -0.5:
        # Override to Shield if extreme panic in news
        status = "SHIELD_ACTIVE"
        
    return {
        "risk_shield_status": status,
        "market_context": {**state["market_context"], "sentiment": sentiment_score},
        "decision_reasoning": f"[Sentinel] Regime: {regime}, Sentiment: {sentiment_score:.2f}."
    }

def strategy_node(state: AgentState):
    """Selects the best trading parameters (Bandit logic)."""
    if state["risk_shield_status"] == "CRISIS":
        return {"trade_proposal": {"action": "HOLD"}, "decision_reasoning": state["decision_reasoning"] + " (CRISIS mode: Trades blocked)"}

    db = SessionLocal()
    try:
        bandit = EpsilonGreedyBandit(db)
        # For now, we reuse the bandit logic to get the 'locked' winner or explore
        # In a full agentic flow, the LLM might tweak these.
        best_arm = bandit.get_best_arm()
        
        # Proposal (Simulating a simple trend-following trigger)
        # In real execution, this would be more complex.
        proposal = {
            "action": "TRADE",
            "params": best_arm,
            "reason": "Bandit Optimized"
        }
        
        return {
            "trade_proposal": proposal,
            "decision_reasoning": state["decision_reasoning"] + f" [Strategy] Selected {best_arm}."
        }
    finally:
        db.close()

def executor_node(state: AgentState):
    """Final check before execution."""
    reasoning = state["decision_reasoning"]
    proposal = state["trade_proposal"]
    
    if proposal["action"] == "HOLD":
        return {"decision_reasoning": reasoning + " [Executor] No action taken."}
    
    # Sentiment override check
    sentiment = state["market_context"].get("sentiment", 0.0)
    if sentiment < -0.3 and proposal["action"] == "TRADE":
         return {
            "trade_proposal": {"action": "HOLD"},
            "decision_reasoning": reasoning + " [Executor] Risk-off: News sentiment too bearish."
        }

    return {"decision_reasoning": reasoning + " [Executor] Finalizing trade execution."}

# --- Router ---

def should_continue(state: AgentState) -> Literal["strategy", "executor"]:
    if state["risk_shield_status"] == "CRISIS":
        return "executor"
    return "strategy"

# --- Graph Definition ---

workflow = StateGraph(AgentState)

workflow.add_node("sentinel", sentinel_node)
workflow.add_node("strategy", strategy_node)
workflow.add_node("executor", executor_node)

workflow.set_entry_point("sentinel")

workflow.add_conditional_edges(
    "sentinel",
    should_continue,
    {
        "strategy": "strategy",
        "executor": "executor"
    }
)

workflow.add_edge("strategy", "executor")
workflow.add_edge("executor", END)

app_graph = workflow.compile()

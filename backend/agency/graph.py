import logging
import os
from typing import Literal
from langgraph.graph import StateGraph, END
from backend.agency.state import AgentState
from backend.agency.sentinel import SentinelShield
from backend.learning import EpsilonGreedyBandit
from backend.db import SessionLocal
from backend.config import TRADED_SYMBOLS, AGENTIC_MODE

logger = logging.getLogger("AgentGraph")

# --- Optional MCP tools for agentic mode ---
_mcp_tools_loaded = False
_mcp_tools = []
_mcp_manager = None


async def _ensure_mcp_tools():
    """Lazily initialise MCP Brain tools the first time they are needed."""
    global _mcp_tools_loaded, _mcp_tools, _mcp_manager
    if _mcp_tools_loaded:
        return _mcp_tools
    try:
        from agent.mcp_client import MCPSessionManager
        _mcp_manager = MCPSessionManager()
        await _mcp_manager.__aenter__()
        _mcp_tools = await _mcp_manager.get_langchain_tools()
        brain_tools = [t for t in _mcp_tools if t.name.startswith("brain_")]
        _mcp_tools = brain_tools
        logger.info(f"AGENTIC_MODE: loaded {len(_mcp_tools)} Brain MCP tools")
    except Exception as e:
        logger.warning(f"AGENTIC_MODE: failed to load MCP tools, continuing without: {e}")
        _mcp_tools = []
    _mcp_tools_loaded = True
    return _mcp_tools


# --- Nodes ---

async def sentinel_node(state: AgentState):
    """Checks VIX and Sentiment to determine if it's safe to trade."""
    sentinel = SentinelShield()

    vix = state["market_context"].get("vix_close", 20.0)
    regime = sentinel.analyze_vix_regime(vix)

    sentiment_score = await sentinel.analyze_sentiment(TRADED_SYMBOLS[:3])

    status = regime
    if sentiment_score < -0.5:
        status = "SHIELD_ACTIVE"

    return {
        "risk_shield_status": status,
        "market_context": {**state["market_context"], "sentiment": sentiment_score},
        "decision_reasoning": f"[Sentinel] Regime: {regime}, Sentiment: {sentiment_score:.2f}.",
    }


async def introspection_node(state: AgentState):
    """
    AGENTIC_MODE only: calls Brain MCP tools (portfolio snapshot, bandit
    analysis, risk status) and appends the context to decision_reasoning
    so downstream nodes have richer information.
    """
    tools = await _ensure_mcp_tools()
    extra_context = []
    for tool in tools:
        if tool.name in ("brain_get_portfolio_snapshot", "brain_get_bandit_analysis", "brain_get_risk_status"):
            try:
                result = await tool.ainvoke({})
                extra_context.append(f"[{tool.name}] {result}")
            except Exception as e:
                logger.warning(f"Introspection tool {tool.name} failed: {e}")

    reasoning = state["decision_reasoning"]
    if extra_context:
        reasoning += " " + " ".join(extra_context)

    return {"decision_reasoning": reasoning}


def strategy_node(state: AgentState):
    """Selects the best trading parameters (Bandit logic)."""
    if state["risk_shield_status"] == "CRISIS":
        return {
            "trade_proposal": {"action": "HOLD"},
            "decision_reasoning": state["decision_reasoning"] + " (CRISIS mode: Trades blocked)",
        }

    db = SessionLocal()
    try:
        bandit = EpsilonGreedyBandit(db)
        best_arm = bandit.get_best_arm()

        proposal = {
            "action": "TRADE",
            "params": best_arm,
            "reason": "Bandit Optimized",
        }

        return {
            "trade_proposal": proposal,
            "decision_reasoning": state["decision_reasoning"] + f" [Strategy] Selected {best_arm}.",
        }
    finally:
        db.close()


def executor_node(state: AgentState):
    """Final check before execution."""
    reasoning = state["decision_reasoning"]
    proposal = state["trade_proposal"]

    if proposal["action"] == "HOLD":
        return {"decision_reasoning": reasoning + " [Executor] No action taken."}

    sentiment = state["market_context"].get("sentiment", 0.0)
    if sentiment < -0.3 and proposal["action"] == "TRADE":
        return {
            "trade_proposal": {"action": "HOLD"},
            "decision_reasoning": reasoning + " [Executor] Risk-off: News sentiment too bearish.",
        }

    return {"decision_reasoning": reasoning + " [Executor] Finalizing trade execution."}


# --- Router ---

def should_continue(state: AgentState) -> Literal["strategy", "executor"]:
    if state["risk_shield_status"] == "CRISIS":
        return "executor"
    return "strategy"


def after_sentinel(state: AgentState) -> Literal["introspection", "strategy", "executor"]:
    if state["risk_shield_status"] == "CRISIS":
        return "executor"
    if AGENTIC_MODE:
        return "introspection"
    return "strategy"


# --- Graph Definition ---

workflow = StateGraph(AgentState)

workflow.add_node("sentinel", sentinel_node)
workflow.add_node("strategy", strategy_node)
workflow.add_node("executor", executor_node)

if AGENTIC_MODE:
    workflow.add_node("introspection", introspection_node)

workflow.set_entry_point("sentinel")

if AGENTIC_MODE:
    workflow.add_conditional_edges(
        "sentinel",
        after_sentinel,
        {
            "introspection": "introspection",
            "strategy": "strategy",
            "executor": "executor",
        },
    )
    workflow.add_edge("introspection", "strategy")
else:
    workflow.add_conditional_edges(
        "sentinel",
        should_continue,
        {
            "strategy": "strategy",
            "executor": "executor",
        },
    )

workflow.add_edge("strategy", "executor")
workflow.add_edge("executor", END)

app_graph = workflow.compile()

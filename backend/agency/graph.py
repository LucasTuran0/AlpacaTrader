import logging
from typing import Literal
from langgraph.graph import StateGraph, END
from backend.agency.state import AgentState
from backend.agency.sentinel import SentinelShield
from backend.learning import EpsilonGreedyBandit
from backend.db import SessionLocal
from backend.config import TRADED_SYMBOLS, AGENTIC_MODE

logger = logging.getLogger("AgentGraph")

# Lazily created on first use so tests can import graph.py without a GOOGLE_API_KEY.
# The single instance is reused across bot cycles so the sentiment cache persists.
_sentinel: "SentinelShield | None" = None


def _get_sentinel() -> SentinelShield:
    global _sentinel
    if _sentinel is None:
        _sentinel = SentinelShield()
    return _sentinel


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
    sentinel = _get_sentinel()
    vix = state["market_context"].get("vix_close", 20.0)
    auto_regime = sentinel.analyze_vix_regime(vix)
    override_mode = state["market_context"].get("risk_override")

    sentiment_score = await sentinel.analyze_sentiment(TRADED_SYMBOLS[:3], vix=vix)

    status = auto_regime
    if override_mode is not None:
        status = override_mode
    elif sentiment_score < -0.5:
        status = "SHIELD_ACTIVE"

    regime_text = f"override={override_mode}" if override_mode is not None else f"auto={auto_regime}"

    return {
        "risk_shield_status": status,
        "market_context": {**state["market_context"], "sentiment": sentiment_score},
        "decision_reasoning": f"[Sentinel] Regime: {regime_text}, Sentiment: {sentiment_score:.2f}.",
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

    if state["market_context"].get("dry_run", False):
        dry_params = {"fast": 20, "slow": 60, "vol_target": 0.10}
        return {
            "trade_proposal": {
                "action": "TRADE",
                "params": dry_params,
                "reason": "Dry run fixed params",
            },
            "decision_reasoning": state["decision_reasoning"] + f" [Strategy] Dry run params {dry_params}.",
        }

    db = SessionLocal()
    try:
        eps = float(state["market_context"].get("epsilon", 0.2))
        bandit = EpsilonGreedyBandit(db, epsilon=eps)
        selected_arm = bandit.choose_arm() if eps > 0 else bandit.get_best_arm()

        proposal = {
            "action": "TRADE",
            "params": selected_arm,
            "reason": f"Bandit epsilon={eps:.2f}",
        }

        return {
            "trade_proposal": proposal,
            "decision_reasoning": state["decision_reasoning"] + f" [Strategy] Selected {selected_arm} (epsilon={eps:.2f}).",
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

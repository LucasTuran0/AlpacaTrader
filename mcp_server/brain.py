from fastmcp import FastMCP
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("BOT_API_URL", "http://localhost:8000")

mcp = FastMCP("PaperPilot Brain")


async def _get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_URL}{path}", params=params, timeout=15.0)
        resp.raise_for_status()
        return resp.json()


async def _post(path: str, body: dict | None = None) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_URL}{path}", json=body, timeout=30.0)
        resp.raise_for_status()
        return resp.json()


# ──────────────────────────────────────────────
# READ-ONLY TOOLS
# ──────────────────────────────────────────────

@mcp.tool()
async def get_portfolio_snapshot() -> str:
    """
    Returns a comprehensive snapshot of the trading bot state in one call:
    account equity, buying power, all current positions with unrealized PnL,
    current VIX regime, and whether trading is currently blocked.
    Use this as the first tool call to understand the full picture.
    """
    try:
        account = await _get("/account")
        risk = await _get("/bot/risk_status")
        metrics = await _get("/bot/metrics")

        snapshot = {
            "account": account,
            "risk": risk,
            "performance": {
                "total_runs": metrics.get("total_runs", 0),
                "current_equity": metrics.get("current_equity", 0),
                "max_drawdown_pct": metrics.get("max_drawdown_pct", 0),
            },
        }
        return json.dumps(snapshot, indent=2)
    except Exception as e:
        return f"Error building portfolio snapshot: {e}"


@mcp.tool()
async def get_bandit_analysis() -> str:
    """
    Returns a detailed analysis of the multi-armed bandit learning state:
    the top 5 best-performing strategy parameter sets, bottom 5 worst,
    and the total number of arms explored. Helps understand which
    fast/slow MA periods and vol targets are working.
    """
    try:
        stats = await _get("/bot/bandit_stats")
        if not stats:
            return "No bandit data available. Run a backtest or live cycle first."

        top_5 = stats[:5]
        bottom_5 = stats[-5:] if len(stats) > 5 else []
        total_trials = sum(s["trials"] for s in stats)

        analysis = {
            "total_arms": len(stats),
            "total_trials": total_trials,
            "top_5_arms": top_5,
            "bottom_5_arms": bottom_5,
        }
        return json.dumps(analysis, indent=2)
    except Exception as e:
        return f"Error fetching bandit analysis: {e}"


@mcp.tool()
async def get_risk_status() -> str:
    """
    Returns the current risk regime of the bot: live VIX value,
    whether the auto-detected regime is SAFE/SHIELD_ACTIVE/CRISIS,
    whether a manual override is active, and if trading is blocked (and why).
    """
    try:
        data = await _get("/bot/risk_status")
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"Error fetching risk status: {e}"


@mcp.tool()
async def get_trade_history(limit: int = 15) -> str:
    """
    Returns the most recent filled trades with entry price, PnL reward,
    which bandit parameters were used, and timestamps. Use this to
    evaluate recent bot performance and understand what trades were made.
    """
    try:
        data = await _get("/bot/trade_history", params={"limit": limit})
        if not data:
            return "No filled trades found yet."
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"Error fetching trade history: {e}"


# ──────────────────────────────────────────────
# ACTION TOOLS
# ──────────────────────────────────────────────

@mcp.tool()
async def set_risk_override(mode: str) -> str:
    """
    Override the automatic VIX-based risk regime. Use 'CRISIS' to halt all
    trading immediately, 'SHIELD_ACTIVE' for defensive mode, 'SAFE' to force
    normal operation, or 'clear' to remove the override and return to auto-detection.
    """
    try:
        actual_mode = None if mode.lower() == "clear" else mode.upper()
        data = await _post("/bot/risk_override", {"mode": actual_mode})
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"Error setting risk override: {e}"


@mcp.tool()
async def adjust_bandit_epsilon(epsilon: float) -> str:
    """
    Change the bandit exploration rate (epsilon). Range: 0.0 to 1.0.
    Higher values = more exploration (try new strategies).
    Lower values = more exploitation (stick with proven winners).
    Set to 0.0 to lock the current best strategy. Set to 0.5 after a
    market regime change to force rapid re-exploration.
    """
    try:
        data = await _post("/bot/bandit_epsilon", {"epsilon": epsilon})
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"Error adjusting epsilon: {e}"


@mcp.tool()
async def force_liquidation() -> str:
    """
    Immediately liquidate ALL managed positions. This cancels all open orders
    and sells all holdings. Use in emergencies or when you want to go fully
    to cash. This action cannot be undone.
    """
    try:
        data = await _post("/bot/force_liquidate")
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"Error triggering liquidation: {e}"


@mcp.tool()
async def strategy_run_once(dry_run: bool = True) -> str:
    """
    Triggers a single bot trading cycle. Set dry_run=True to simulate
    without placing real orders, or dry_run=False to execute live trades.
    Returns the decision details including parameters used and orders placed.
    """
    try:
        data = await _post("/bot/run_once", {"dry_run": dry_run})
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"Error running strategy: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")

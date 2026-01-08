from fastmcp import FastMCP
import httpx
import os
from dotenv import load_dotenv

# Load env in case we need it, though requests go to localhost:8000
load_dotenv()

# We point to the local FastAPI for bot logic
API_URL = "http://localhost:8012"

mcp = FastMCP("PaperPilot Brain")

@mcp.tool()
async def strategy_run_once(dry_run: bool = True) -> str:
    """
    Triggers the bot's strategy calculation and execution logic.
    Returns the JSON response describing the decision.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{API_URL}/bot/run_once", 
                json={"dry_run": dry_run},
                timeout=30.0
            )
            resp.raise_for_status()
            return str(resp.json())
        except Exception as e:
            return f"Error running strategy: {str(e)}"

@mcp.tool()
async def bot_get_metrics() -> str:
    """
    Fetches the latest bot performance metrics (PnL, Drawdown, Run Count).
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{API_URL}/bot/metrics", timeout=10.0)
            resp.raise_for_status()
            return str(resp.json())
        except Exception as e:
            return f"Error fetching metrics: {str(e)}"

@mcp.tool()
async def bot_get_logs(limit: int = 5) -> str:
    """
    Fetches the most recent decision logs.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{API_URL}/bot/logs", 
                params={"limit": limit}, 
                timeout=10.0
            )
            resp.raise_for_status()
            return str(resp.json())
        except Exception as e:
            return f"Error fetching logs: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")

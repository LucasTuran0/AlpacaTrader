import asyncio
import os
from dotenv import load_dotenv
from backend.agency.executor import AgenticExecutor
from backend.db import SessionLocal

# Mock Market Context
mock_context = {
    "equity": 100000.0,
    "vix_close": 15.0,
    "latest_prices": {"AAPL": 150.0}
}

async def debug_agent():
    load_dotenv("backend/.env")
    print("🤖 Starting Agentic Flow Debug Test...")
    
    executor = AgenticExecutor()
    result = await executor.run(mock_context)
    
    print("\n--- FINAL AGENT STATE ---")
    print(f"Risk Shield: {result['risk_shield_status']}")
    print(f"Decision: {result['trade_proposal']['action']}")
    print(f"Reasoning: {result['decision_reasoning']}")
    
    if "params" in result['trade_proposal']:
        print(f"Proposed Params: {result['trade_proposal']['params']}")

if __name__ == "__main__":
    asyncio.run(debug_agent())

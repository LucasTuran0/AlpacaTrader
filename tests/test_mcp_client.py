import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import sys
import os

from dotenv import load_dotenv

load_dotenv("backend/.env")

# Set env for subprocesses
env = os.environ.copy()
env["ALPACA_API_KEY"] = os.getenv("ALPACA_API_KEY", "")
env["ALPACA_SECRET_KEY"] = os.getenv("ALPACA_API_SECRET", "")
env["ALPACA_PAPER"] = "True"

async def test_brain():
    print("--- Testing Custom Brain MCP ---")
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server/brain.py"],
        env=env
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List tools
            tools = await session.list_tools()
            print(f"Brain Tools: {[t.name for t in tools.tools]}")
            
            # Call metrics (should fail if bot server 8000 not running, but we check connectivity)
            try:
                result = await session.call_tool("bot_get_metrics", {})
                print(f"Metrics Result: {result.content[0].text[:100]}...")
            except Exception as e:
                print(f"Metrics Call Error (Expected if main bot execution skipped): {e}")

async def test_official():
    print("\n--- Testing Official Alpaca MCP ---")
    # Official server entry point is via 'alpaca-mcp-server' command or module 'alpaca_mcp_server.cli'
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "alpaca_mcp_server.cli", "serve"], 
        env=env
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                tools = await session.list_tools()
                print(f"Official Tools: {[t.name for t in tools.tools]}")
                
                # Fetch Account
                acct = await session.call_tool("get_account", {})
                print(f"Account: {str(acct.content[0].text)[:100]}...")
    except Exception as e:
         print(f"Official Server Launch Error: {e}")

async def main():
    await test_brain()
    await test_official()

if __name__ == "__main__":
    asyncio.run(main())

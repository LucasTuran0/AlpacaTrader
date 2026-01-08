import asyncio
import os
import sys
from typing import List, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.tools import Tool, StructuredTool # Correct import for newer langchain
from pydantic import BaseModel, Field

# Load env variables for the subprocesses
def get_env():
    env = os.environ.copy()
    # Ensure keys are present if available
    env["ALPACA_API_KEY"] = os.getenv("ALPACA_API_KEY", "")
    env["ALPACA_SECRET_KEY"] = os.getenv("ALPACA_API_SECRET", "") # remap standard to what official server expects
    env["ALPACA_PAPER"] = "True"
    return env

class MCPToolAdapter:
    """
    Connects to an MCP server and adapts its tools to LangChain Tools.
    """
    def __init__(self, command: str, args: List[str], server_name: str):
        self.command = command
        self.args = args
        self.server_name = server_name
        self.server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=get_env()
        )
        self.tools = []

    async def initialize(self):
        # We need a way to keep the session open. 
        # For simplicity in this script, we'll fetch schemas once and 
        # recreate sessions for calls (inefficient but distinct for MVP),
        # OR we keep a persistent session manager. 
        # BETTER: Use a context manager wrapper for the whole agent run.
        pass

    async def get_langchain_tools(self) -> List[Tool]:
        # Connect briefly to fetch tool definitions
        tools_out = []
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # Define essential tools to avoid distracting the agent
                ESSENTIAL_TOOLS = {
                    'get_account_info',
                    'get_all_positions', 
                    'get_open_position',
                    'place_stock_order',
                    'cancel_order_by_id',
                    'cancel_all_orders',
                    'get_stock_bars',
                }

                mcp_tools = await session.list_tools()

                for t in mcp_tools.tools:
                    # Filter official alpaca tools
                    if self.server_name == 'alpaca' and t.name not in ESSENTIAL_TOOLS:
                        continue
                        
                    # Capture closure variables
                    tool_name = t.name
                    tool_desc = t.description or ""
                    
                    # Create a sync wrapper that launches a new ephemeral session to call the tool
                    # This is heavy but robust against stdio concurrency issues for now.
                    # In production, we'd use a long-lived server process manager.
                    
                    async def _async_tool_func(**kwargs):
                        # Re-connect for execution
                        async with stdio_client(self.server_params) as (r, w):
                            async with ClientSession(r, w) as s:
                                await s.initialize()
                                result = await s.call_tool(tool_name, kwargs)
                                return result.content[0].text

                    # Create StructuredTool if schema is complex, or simple Tool
                    # For MVP, we'll use StructuredTool.from_function pattern manually
                    # but since schema is dynamic, we define a wrapper class or use StructuredTool directly
                    
                    # Hack for simple binding:
                    # We accept **kwargs and pass them through.
                    
                    # We need to define the schema model dyamically if we want validation,
                    # but for now we'll rely on the LLM to just pass args as Dict.
                    
                    tools_out.append(StructuredTool.from_function(
                        func=None, # Sync
                        coroutine=_async_tool_func, # Async
                        name=f"{self.server_name}_{tool_name}", # Namespaced
                        description=tool_desc
                    ))
                    
        return tools_out

# Factory to get all tools
async def get_all_mcp_tools():
    # 1. Official Server
    official = MCPToolAdapter(
        command=sys.executable,
        args=["-m", "alpaca_mcp_server.cli", "serve"],
        server_name="alpaca"
    )
    
    # 2. Brain Server
    brain = MCPToolAdapter(
        command=sys.executable,
        args=["mcp_server/brain.py"],
        server_name="brain"
    )
    
    t1 = await official.get_langchain_tools()
    t2 = await brain.get_langchain_tools()
    return t1 + t2

import asyncio
import logging
import os
import sys
from typing import List, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.tools import StructuredTool

logger = logging.getLogger("MCPClient")


def get_env():
    env = os.environ.copy()
    env["ALPACA_API_KEY"] = os.getenv("ALPACA_API_KEY", "")
    env["ALPACA_SECRET_KEY"] = os.getenv("ALPACA_API_SECRET", "")
    env["ALPACA_PAPER"] = "True"
    return env


class PersistentMCPSession:
    """
    Keeps a single MCP subprocess + session alive for the lifetime of the
    agent run, rather than spawning a new process for every tool call.
    """

    def __init__(self, server_params: StdioServerParameters, server_name: str):
        self.server_params = server_params
        self.server_name = server_name
        self._session: ClientSession | None = None
        self._exit_stack: list[Any] = []

    async def connect(self):
        ctx_client = stdio_client(self.server_params)
        transport = await ctx_client.__aenter__()
        self._exit_stack.append(ctx_client)

        read_stream, write_stream = transport
        ctx_session = ClientSession(read_stream, write_stream)
        self._session = await ctx_session.__aenter__()
        self._exit_stack.append(ctx_session)

        await self._session.initialize()
        logger.info(f"Persistent MCP session established: {self.server_name}")

    async def call_tool(self, name: str, kwargs: dict) -> str:
        if self._session is None:
            raise RuntimeError(f"MCP session not connected for {self.server_name}")
        result = await self._session.call_tool(name, kwargs)
        return result.content[0].text

    async def list_tools(self):
        if self._session is None:
            raise RuntimeError(f"MCP session not connected for {self.server_name}")
        return await self._session.list_tools()

    async def close(self):
        for ctx in reversed(self._exit_stack):
            try:
                await ctx.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing MCP context for {self.server_name}: {e}")
        self._exit_stack.clear()
        self._session = None
        logger.info(f"MCP session closed: {self.server_name}")


class MCPSessionManager:
    """
    Manages persistent sessions for all MCP servers. Designed to be used as
    an async context manager around the full agent run.
    """

    ESSENTIAL_ALPACA_TOOLS = {
        "get_account_info",
        "get_all_positions",
        "get_open_position",
        "place_stock_order",
        "cancel_order_by_id",
        "cancel_all_orders",
        "get_stock_bars",
    }

    def __init__(self):
        env = get_env()
        self._sessions: list[PersistentMCPSession] = [
            PersistentMCPSession(
                StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "alpaca_mcp_server.cli", "serve"],
                    env=env,
                ),
                server_name="alpaca",
            ),
            PersistentMCPSession(
                StdioServerParameters(
                    command=sys.executable,
                    args=["mcp_server/brain.py"],
                    env=env,
                ),
                server_name="brain",
            ),
        ]

    async def __aenter__(self):
        for session in self._sessions:
            await session.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for session in self._sessions:
            await session.close()

    async def get_langchain_tools(self) -> List[StructuredTool]:
        tools_out: list[StructuredTool] = []

        for session in self._sessions:
            mcp_tools = await session.list_tools()

            for t in mcp_tools.tools:
                if session.server_name == "alpaca" and t.name not in self.ESSENTIAL_ALPACA_TOOLS:
                    continue

                tool_name = t.name
                tool_desc = t.description or ""

                def _make_tool_func(captured_session: PersistentMCPSession, captured_name: str):
                    async def _invoke(**kwargs):
                        return await captured_session.call_tool(captured_name, kwargs)
                    return _invoke

                tools_out.append(
                    StructuredTool.from_function(
                        func=None,
                        coroutine=_make_tool_func(session, tool_name),
                        name=f"{session.server_name}_{tool_name}",
                        description=tool_desc,
                    )
                )

        return tools_out


# Backward-compatible convenience function for scripts that don't need persistence
async def get_all_mcp_tools():
    manager = MCPSessionManager()
    await manager.__aenter__()
    return await manager.get_langchain_tools(), manager

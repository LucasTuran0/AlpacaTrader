from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, BaseMessage
from agent.mcp_client import MCPSessionManager
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")


class AgentState(TypedDict):
    messages: List[BaseMessage]


class PaperPilotAgent:
    def __init__(self):
        self.model = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0)
        self.tools = []
        self.graph = None
        self._session_manager: MCPSessionManager | None = None

    async def initialize(self):
        self._session_manager = MCPSessionManager()
        await self._session_manager.__aenter__()
        self.tools = await self._session_manager.get_langchain_tools()

        self.model = self.model.bind_tools(self.tools)

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self.call_model)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", self.should_continue)
        workflow.add_edge("tools", "agent")
        self.graph = workflow.compile()

    def should_continue(self, state: AgentState):
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tools"
        return END

    async def call_model(self, state: AgentState):
        response = await self.model.ainvoke(state["messages"])
        return {"messages": [response]}

    async def run(self, input_text: str):
        if not self.graph:
            await self.initialize()

        initial_state = {"messages": [HumanMessage(content=input_text)]}
        async for event in self.graph.astream(initial_state):
            for value in event.values():
                if "messages" in value:
                    print(f"Agent: {value['messages'][-1].content}")

    async def close(self):
        if self._session_manager:
            await self._session_manager.__aexit__(None, None, None)
            self._session_manager = None

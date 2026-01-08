from typing import Annotated, TypedDict, List
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, BaseMessage
from agent.mcp_client import get_all_mcp_tools
import os
from dotenv import load_dotenv

# Load env for Keys
load_dotenv("backend/.env")

class AgentState(TypedDict):
    messages: List[BaseMessage]

class PaperPilotAgent:
    def __init__(self):
        # Using gemini-flash-latest as identified from available models
        self.model = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0)
        self.tools = []
        self.graph = None

    async def initialize(self):
        # 1. Fetch tools from MCP servers
        self.tools = await get_all_mcp_tools()
        
        # 2. Bind tools to model
        self.model = self.model.bind_tools(self.tools)
        
        # 3. Define Graph
        workflow = StateGraph(AgentState)
        
        # Nodes
        workflow.add_node("agent", self.call_model)
        workflow.add_node("tools", ToolNode(self.tools))
        
        # Edges
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

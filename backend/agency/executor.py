from backend.agency.graph import app_graph
import logging

logger = logging.getLogger("AgenticExecutor")

class AgenticExecutor:
    async def run(self, market_context: dict):
        """
        Runs the full agentic flow and returns the final state.
        """
        initial_state = {
            "messages": [],
            "market_context": market_context,
            "trade_proposal": {"action": "HOLD"},
            "risk_shield_status": "SAFE",
            "decision_reasoning": ""
        }
        
        final_state = await app_graph.ainvoke(initial_state)
        return final_state

import os
import json
from sqlalchemy.orm import Session
from backend.models import Decision, BanditState
from backend.learning import EpsilonGreedyBandit
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv("backend/.env")

class StrategyAdvisor:
    def __init__(self, db: Session):
        self.db = db
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.2
        )

    def perform_retrospective(self, days_back: int = 30):
        """Analyze recent trades and suggest Bandit adjustments."""
        # 1. Fetch recent decisions with negative rewards (failures)
        failures = self.db.query(Decision).filter(
            Decision.reward < 0
        ).order_by(Decision.timestamp.desc()).limit(20).all()

        # 2. Fetch top successes
        successes = self.db.query(Decision).filter(
            Decision.reward > 100
        ).order_by(Decision.timestamp.desc()).limit(20).all()

        if not failures and not successes:
            return "Not enough diversified data to perform a retrospective."

        # 3. Create context for LLM
        history_summary = []
        for d in failures + successes:
            history_summary.append({
                "params": d.params_used,
                "reasoning": d.reasoning,
                "pnl": d.reward
            })

        prompt = PromptTemplate.from_template("""
        You are the PaperPilot Quantitative Strategist. 
        Below is a summary of recent trades made by our Contextual Bandit bot.
        Every trade has a 'reasoning' (what the bot was thinking) and a 'pnl' (the outcome).
        
        Recent Trade Trace:
        {history}

        Analyze the patterns. Which parameter sets (fast/slow) are consistently failing during specific trends?
        Which ones are winning?
        
        Suggest exactly 3 "Strategic Adjustments". 
        Format as JSON: {{"adjustments": [{{"param_key": "20_60_0.1", "weight_delta": -50.0, "reason": "..."}}]}}
        - weight_delta: A negative number to discourage a bad strategy, positive to encourage a good one.
        """)

        chain = prompt | self.llm
        response = chain.invoke({"history": json.dumps(history_summary)})
        
        try:
            # Simple direct parse or clean if needed
            cleaned_content = response.content.replace("```json", "").replace("```", "").strip()
            advice = json.loads(cleaned_content)
            
            # 4. Apply "Virtual Feedback" to the Bandit
            bandit = EpsilonGreedyBandit(self.db)
            applied = []
            for adj in advice.get("adjustments", []):
                key = adj["param_key"]
                delta = adj["weight_delta"]
                # Update reward in DB
                bandit.update_reward(key, delta)
                applied.append(f"Adjusted {key} by {delta}: {adj['reason']}")
            
            return "\n".join(applied)
        except Exception as e:
            return f"Failed to process advisor logic: {e}. Raw: {response.content}"

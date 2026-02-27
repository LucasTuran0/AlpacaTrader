import os
import json
import logging
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from backend.market_data import MarketDataProvider

logger = logging.getLogger("Sentinel")

class SentinelShield:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.0
        )
        self.provider = MarketDataProvider()

    def analyze_vix_regime(self, vix_price: float) -> str:
        """Detect risk regime based on VIX."""
        if vix_price >= 30:
            return "CRISIS"
        elif vix_price >= 20:
            return "SHIELD_ACTIVE"
        else:
            return "SAFE"

    async def analyze_sentiment(self, symbols: List[str]) -> float:
        """
        Fetches news and returns a sentiment score from -1.0 (very bearish) to 1.0 (very bullish).
        """
        try:
            headlines = []
            for symbol in symbols:
                news = self.provider.get_news([symbol], limit=5)
                if news is None:
                    continue
                for item in news:
                    headline = item.get("headline") if isinstance(item, dict) else getattr(item, "headline", "")
                    if headline:
                        headlines.append(f"[{symbol}] {headline}")

            if not headlines:
                return 0.0 # Neutral if no news

            prompt = PromptTemplate.from_template("""
            You are a Financial Sentiment Analyzer. 
            Analyze the following headlines and provide a combined sentiment score between -1.0 (extremely bearish) and 1.0 (extremely bullish).
            Output ONLY the float number.

            Headlines:
            {headlines}
            """)

            chain = prompt | self.llm
            response = await chain.ainvoke({"headlines": "\n".join(headlines)})
            
            try:
                score = float(response.content.strip())
                return max(-1.0, min(1.0, score))
            except:
                logger.warning(f"Failed to parse sentiment score from: {response.content}")
                return 0.0

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return 0.0

if __name__ == "__main__":
    # Quick test
    import asyncio
    from dotenv import load_dotenv
    load_dotenv("backend/.env")
    
    async def test():
        s = SentinelShield()
        regime = s.analyze_vix_regime(25.0)
        print(f"VIX 25 Regime: {regime}")
        sentiment = await s.analyze_sentiment(["AAPL", "TSLA"])
        print(f"Sentiment Score: {sentiment}")

    asyncio.run(test())

import os
import time
import logging
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from backend.market_data import MarketDataProvider

logger = logging.getLogger("Sentinel")

# How long (seconds) to reuse a cached sentiment verdict.
_SENTIMENT_TTL = int(os.getenv("SENTINEL_TTL_SECONDS", "300"))
# Re-call the LLM if VIX moves by more than this many points.
_VIX_DELTA_THRESHOLD = float(os.getenv("SENTINEL_VIX_DELTA", "1.5"))


class SentinelShield:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-lite-latest",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.0
        )
        self.provider = MarketDataProvider()
        self._init_cache()

    def analyze_vix_regime(self, vix_price: float) -> str:
        """Detect risk regime based on VIX."""
        if vix_price >= 30:
            return "CRISIS"
        elif vix_price >= 20:
            return "SHIELD_ACTIVE"
        else:
            return "SAFE"

    def _init_cache(self) -> None:
        self._cached_score: float = 0.0
        self._last_vix: float = -999.0
        self._last_called: float = 0.0

    def _update_cache(self, score: float, vix: float) -> None:
        self._cached_score = score
        self._last_vix = vix
        self._last_called = time.monotonic()
        logger.info(f"Sentinel cache updated: score={score:.2f}, vix={vix:.2f}")

    async def analyze_sentiment(self, symbols: List[str], vix: float = 0.0) -> float:
        """
        Fetches news and returns a sentiment score from -1.0 (very bearish) to 1.0 (very bullish).

        Results are cached for up to SENTINEL_TTL_SECONDS (default 300s) and
        only refreshed when VIX moves more than SENTINEL_VIX_DELTA (default 1.5)
        points, to stay within free-tier Gemini quota limits.
        """
        now = time.monotonic()
        last_vix = getattr(self, "_last_vix", -999.0)
        last_called = getattr(self, "_last_called", 0.0)
        vix_moved = abs(vix - last_vix) >= _VIX_DELTA_THRESHOLD
        ttl_expired = (now - last_called) >= _SENTIMENT_TTL

        cached_score = getattr(self, "_cached_score", 0.0)
        if not vix_moved and not ttl_expired:
            logger.debug(
                f"Sentinel cache hit (age {now - last_called:.0f}s, "
                f"ΔVIX {abs(vix - last_vix):.2f}) → {cached_score:.2f}"
            )
            return cached_score

        try:
            headlines = []
            for symbol in symbols:
                news = self.provider.get_news([symbol], limit=5)
                if news is None:
                    continue
                # NewsSet stores articles under .data["news"]; fall back to
                # iterating directly if a list/raw dict was returned instead.
                if hasattr(news, "data") and isinstance(news.data, dict):
                    articles = news.data.get("news", [])
                elif isinstance(news, dict):
                    articles = news.get("news", [])
                else:
                    articles = list(news) if news else []

                for item in articles:
                    if isinstance(item, dict):
                        headline = item.get("headline", "")
                    else:
                        headline = getattr(item, "headline", "") or ""
                    if headline:
                        headlines.append(f"[{symbol}] {headline}")

            if not headlines:
                self._update_cache(0.0, vix)
                return 0.0  # Neutral if no news

            prompt = PromptTemplate.from_template("""
            You are a Financial Sentiment Analyzer. 
            Analyze the following headlines and provide a combined sentiment score between -1.0 (extremely bearish) and 1.0 (extremely bullish).
            Output ONLY the float number.

            Headlines:
            {headlines}
            """)

            chain = prompt | self.llm
            response = await chain.ainvoke({"headlines": "\n".join(headlines)})

            # Newer langchain-google-genai returns structured content as a
            # list of parts (e.g. [{"type": "text", "text": "0.35", ...}]).
            # Older versions return a plain string. Handle both.
            raw_content = response.content
            if isinstance(raw_content, list):
                text = "".join(
                    (part.get("text", "") if isinstance(part, dict) else str(part))
                    for part in raw_content
                ).strip()
            else:
                text = str(raw_content).strip()

            # Pull the first numeric token in case the model added prose.
            import re
            match = re.search(r"-?\d+(?:\.\d+)?", text)
            if not match:
                logger.warning(f"Failed to parse sentiment score from: {raw_content!r}")
                return cached_score
            try:
                score = max(-1.0, min(1.0, float(match.group(0))))
                self._update_cache(score, vix)
                return score
            except ValueError:
                logger.warning(f"Failed to parse sentiment score from: {raw_content!r}")
                return cached_score

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return cached_score  # serve stale score rather than resetting to 0.0

if __name__ == "__main__":
    # Quick test
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    
    async def test():
        s = SentinelShield()
        regime = s.analyze_vix_regime(25.0)
        print(f"VIX 25 Regime: {regime}")
        sentiment = await s.analyze_sentiment(["AAPL", "TSLA"])
        print(f"Sentiment Score: {sentiment}")

    asyncio.run(test())

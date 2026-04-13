import os
import time
import logging
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from alpaca.data.historical import StockHistoricalDataClient, NewsClient
from alpaca.data.requests import StockBarsRequest, NewsRequest
from alpaca.data.timeframe import TimeFrame

logger = logging.getLogger("MarketData")

class MarketDataProvider:
    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.api_secret = os.getenv("ALPACA_API_SECRET")
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Missing ALPACA_API_KEY / ALPACA_API_SECRET")
        
        self.client = StockHistoricalDataClient(self.api_key, self.api_secret)
        self.news_client = NewsClient(self.api_key, self.api_secret)
        self._vix_cache = {"value": 20.0, "timestamp": 0.0}
        self._vix_cache_ttl = 300  # 5 minutes

    def get_bars(self, symbols: list[str], lookback_days: int = 365, timeframe: TimeFrame = TimeFrame.Day) -> pd.DataFrame:
        """
        Fetches bars for the given symbols and timeframe.
        """
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=lookback_days)

        request_params = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=timeframe,
            start=start_dt,
            end=end_dt
        )

        bars = self.client.get_stock_bars(request_params)
        
        # Convert to DataFrame
        df = bars.df
        
        # Ensure standard columns if needed, though alpaca-py returns: 
        # index: [symbol, timestamp]
        # columns: [open, high, low, close, volume, trade_count, vwap]
        
        return df

    def get_news(self, symbols: list[str], limit: int = 10) -> list:
        """
        Fetches recent news headlines for the given symbols.
        """
        request_params = NewsRequest(
            symbols=symbols,
            limit=limit
        )
        news = self.news_client.get_news(request_params)
        return news

    def get_vix(self) -> float:
        """Fetches the latest VIX close price with a 5-minute cache."""
        now = time.time()
        if (now - self._vix_cache["timestamp"]) < self._vix_cache_ttl:
            return self._vix_cache["value"]
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="2d")
            if not hist.empty:
                value = float(hist["Close"].iloc[-1])
                self._vix_cache = {"value": value, "timestamp": now}
                logger.info(f"VIX fetched: {value:.2f}")
                return value
        except Exception as e:
            logger.warning(f"Failed to fetch VIX, using cached value: {e}")
        return self._vix_cache["value"]

    def get_latest_trades(self, symbols: list[str]) -> dict:
        """
        Fetches the very latest trade for the given symbols.
        Returns a dict {symbol: TradeObject}.
        """
        from alpaca.data.requests import StockLatestTradeRequest
        
        req = StockLatestTradeRequest(symbol_or_symbols=symbols)
        trades = self.client.get_stock_latest_trade(req)
        return trades

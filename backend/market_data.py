import os
from datetime import datetime, timedelta
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient, NewsClient
from alpaca.data.requests import StockBarsRequest, NewsRequest
from alpaca.data.timeframe import TimeFrame

class MarketDataProvider:
    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.api_secret = os.getenv("ALPACA_API_SECRET")
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Missing ALPACA_API_KEY / ALPACA_API_SECRET")
        
        self.client = StockHistoricalDataClient(self.api_key, self.api_secret)
        self.news_client = NewsClient(self.api_key, self.api_secret)

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
        # Some versions of alpaca-py expect a comma-separated string or handle lists differently
        # Let's try combining them if it's a list
        syms = ",".join(symbols) if isinstance(symbols, list) else symbols
        request_params = NewsRequest(
            symbols=syms,
            limit=limit
        )
        news = self.news_client.get_news(request_params)
    def get_latest_trades(self, symbols: list[str]) -> dict:
        """
        Fetches the very latest trade for the given symbols.
        Returns a dict {symbol: TradeObject}.
        """
        from alpaca.data.requests import StockLatestTradeRequest
        
        req = StockLatestTradeRequest(symbol_or_symbols=symbols)
        trades = self.client.get_stock_latest_trade(req)
        return trades

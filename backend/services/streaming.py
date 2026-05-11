import asyncio
import logging
import os
from alpaca.data.live import StockDataStream
from alpaca.trading.stream import TradingStream
from backend.config import TRADED_SYMBOLS
from dotenv import load_dotenv

logger = logging.getLogger("StreamingService")

class AlpacaStreamingService:
    def __init__(self, data_callback, trade_callback):
        load_dotenv()
        self._api_key = os.getenv("ALPACA_API_KEY")
        self._secret_key = os.getenv("ALPACA_API_SECRET")
        self._paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
        
        self.data_callback = data_callback
        self.trade_callback = trade_callback
        self.symbols = TRADED_SYMBOLS
        self._stopping = False
        
        self.last_prices = {s: 0.0 for s in self.symbols}
        self.last_trigger_times = {s: 0.0 for s in self.symbols}
        self.threshold = 0.001
        self.heartbeat_sec = 30
        self.min_cooldown_sec = 10
        self.global_last_trigger = 0.0

        self._init_streams()

    def _init_streams(self):
        self.data_stream = StockDataStream(self._api_key, self._secret_key)
        self.trade_stream = TradingStream(self._api_key, self._secret_key, paper=self._paper)

    async def _on_data(self, data):
        symbol = data.symbol
        price = data.price
        
        prev_price = self.last_prices.get(symbol, 0.0)
        if prev_price == 0:
            self.last_prices[symbol] = price
            return

        move_pct = abs(price - prev_price) / prev_price
        now = asyncio.get_event_loop().time()
        time_since_last = now - self.last_trigger_times.get(symbol, 0.0)

        if (move_pct >= self.threshold or time_since_last >= self.heartbeat_sec):
            if (now - self.global_last_trigger) < self.min_cooldown_sec:
                return

            logger.info(f"PREY DETECTED: {symbol} at {price} (Move: {move_pct:.4%})")
            self.last_prices[symbol] = price
            self.last_trigger_times[symbol] = now
            self.global_last_trigger = now
            await self.data_callback()

    async def _on_trade_update(self, data):
        logger.info(f"TRADE UPDATE: {data.event} for {data.order.symbol}")
        await self.trade_callback(data)

    async def _run_data_stream_with_reconnect(self):
        backoff = 1
        while not self._stopping:
            try:
                self.data_stream.subscribe_trades(self._on_data, *self.symbols)
                await asyncio.to_thread(self.data_stream.run)
            except Exception as e:
                if self._stopping:
                    return
                logger.error(f"Data stream disconnected: {e}. Reconnecting in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
                self._init_streams()
            else:
                backoff = 1

    async def _run_trade_stream_with_reconnect(self):
        backoff = 1
        while not self._stopping:
            try:
                self.trade_stream.subscribe_trade_updates(self._on_trade_update)
                await self.trade_stream._run_forever()
            except Exception as e:
                if self._stopping:
                    return
                logger.error(f"Trade stream disconnected: {e}. Reconnecting in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
                self._init_streams()
            else:
                backoff = 1

    async def start(self):
        logger.info("Starting data and trade streams with auto-reconnect...")
        asyncio.create_task(self._run_data_stream_with_reconnect())
        await self._run_trade_stream_with_reconnect()

    async def stop(self):
        logger.info("Stopping Streams...")
        self._stopping = True
        try:
            await self.data_stream.stop()
        except Exception:
            pass
        try:
            await self.trade_stream.stop()
        except Exception:
            pass

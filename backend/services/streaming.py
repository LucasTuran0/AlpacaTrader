import asyncio
import logging
import os
from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest
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

        self._data_client = StockHistoricalDataClient(self._api_key, self._secret_key)
        self.trade_stream = None

    # ── REST-based market data polling ────────────────────────────────────────

    async def _run_data_polling(self):
        """Poll latest trades via REST instead of WebSocket to avoid connection limits."""
        logger.info("Starting REST market-data polling loop...")
        backoff = 5
        while not self._stopping:
            try:
                req = StockLatestTradeRequest(symbol_or_symbols=self.symbols)
                latest = self._data_client.get_stock_latest_trade(req)

                now = asyncio.get_event_loop().time()
                triggered = False

                for symbol in self.symbols:
                    if symbol not in latest:
                        continue
                    price = float(latest[symbol].price)
                    prev = self.last_prices.get(symbol, 0.0)

                    if prev == 0.0:
                        self.last_prices[symbol] = price
                        continue

                    move_pct = abs(price - prev) / prev
                    time_since_last = now - self.last_trigger_times.get(symbol, 0.0)

                    if move_pct >= self.threshold or time_since_last >= self.heartbeat_sec:
                        if not triggered and (now - self.global_last_trigger) >= self.min_cooldown_sec:
                            logger.info(f"PREY DETECTED: {symbol} @ {price} (Δ {move_pct:.4%})")
                            self.last_prices[symbol] = price
                            self.last_trigger_times[symbol] = now
                            self.global_last_trigger = now
                            triggered = True
                            await self.data_callback()
                    else:
                        self.last_prices[symbol] = price

                backoff = 5
                await asyncio.sleep(self.heartbeat_sec)

            except Exception as e:
                if self._stopping:
                    return
                logger.error(f"Market-data poll error: {e}. Retrying in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    # ── WebSocket trading stream (order fills) ─────────────────────────────────

    def _new_trade_stream(self):
        stream = TradingStream(self._api_key, self._secret_key, paper=self._paper)
        stream.subscribe_trade_updates(self._on_trade_update)
        return stream

    async def _close_trade_stream(self):
        if self.trade_stream is not None:
            try:
                await self.trade_stream.stop()
            except Exception:
                pass
            self.trade_stream = None

    async def _on_trade_update(self, data):
        logger.info(f"TRADE UPDATE: {data.event} for {data.order.symbol}")
        await self.trade_callback(data)

    async def _run_trade_stream_with_reconnect(self):
        backoff = 1
        while not self._stopping:
            try:
                await self._close_trade_stream()
                self.trade_stream = self._new_trade_stream()
                await self.trade_stream._run_forever()
            except Exception as e:
                if self._stopping:
                    return
                logger.error(f"Trade stream disconnected: {e}. Reconnecting in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
            else:
                backoff = 1

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def start(self):
        logger.info("Starting market-data polling + trade stream...")
        asyncio.create_task(self._run_data_polling())
        await self._run_trade_stream_with_reconnect()

    async def stop(self):
        logger.info("Stopping streaming service...")
        self._stopping = True
        await self._close_trade_stream()

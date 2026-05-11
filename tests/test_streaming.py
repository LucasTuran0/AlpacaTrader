import asyncio
import logging
import os
from backend.services.streaming import AlpacaStreamingService
import pytest

pytestmark = pytest.mark.integration

if os.getenv("RUN_STREAMING_TESTS", "0") != "1":
    pytestmark = [pytest.mark.integration, pytest.mark.skip(reason="Set RUN_STREAMING_TESTS=1 to run live streaming connectivity test")]

async def mock_data_callback():
    print(" Data Callback Triggered! The bot would now execute its cycle.")

async def mock_trade_callback(data):
    print(f" Trade Update: {data}")

async def test_streaming_connectivity():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("TestStream")
    
    logger.info(" Testing Alpaca WebSocket Connectivity...")
    
    service = AlpacaStreamingService(mock_data_callback, mock_trade_callback)
    stream_task = None
    
    try:
        stream_task = asyncio.create_task(service.start())
        
        logger.info(" Waiting 30 seconds for live bars...")
        await asyncio.sleep(30)
        
        logger.info(" Connection test finished.")
    except Exception as e:
        logger.error(f" Connection failed: {e}")
    finally:
        await asyncio.wait_for(service.stop(), timeout=10)
        if stream_task:
            stream_task.cancel()
            await asyncio.gather(stream_task, return_exceptions=True)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(test_streaming_connectivity())

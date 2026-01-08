import asyncio
import logging
import os
from backend.services.streaming import AlpacaStreamingService
from dotenv import load_dotenv

async def mock_callback():
    print("🎯 Callback Triggered! The bot would now execute its cycle.")

async def test_streaming_connectivity():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("TestStream")
    
    logger.info("📡 Testing Alpaca WebSocket Connectivity...")
    
    # We only listen for 30 seconds to confirm it connects and doesn't crash
    service = AlpacaStreamingService(mock_callback)
    
    try:
        # Run the stream in a task
        stream_task = asyncio.create_task(service.start())
        
        logger.info("⏳ Waiting 30 seconds for live bars...")
        await asyncio.sleep(30)
        
        logger.info("✅ Connection test finished.")
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
    finally:
        service.stop()
        await asyncio.sleep(2) # Graceful shutdown

if __name__ == "__main__":
    asyncio.run(test_streaming_connectivity())

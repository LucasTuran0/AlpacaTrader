import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import asyncio
import sys
from agent.graph import PaperPilotAgent
from dotenv import load_dotenv

# Load backend env for keys
# Load backend env for keys
env_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
load_dotenv(env_path)

async def main():
    if len(sys.argv) < 2:
        print("Usage: python run_agent.py 'Your query here'")
        sys.exit(1)
        
    query = sys.argv[1]
    
    print(f"--- PaperPilot Agent ---")
    print(f"Goal: {query}")
    print(f"------------------------")
    
    agent = PaperPilotAgent()
    try:
        await agent.run(query)
    except Exception as e:
        print(f"\n[!] Agent stopped with error: {e}")
        # We can try to inspect the graph state if we had access, but for now just acknowledge.

if __name__ == "__main__":
    asyncio.run(main())

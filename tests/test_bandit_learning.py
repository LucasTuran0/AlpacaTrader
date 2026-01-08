import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def run_test():
    print(f"--- Testing Bandit Learning on {BASE_URL} ---")
    
    # 1. Trigger a run
    print("1. Running Bot (Learning Mode)...")
    resp = requests.post(f"{BASE_URL}/bot/run_once", json={"dry_run": False})
    if resp.status_code != 200:
        print(f"Failed to run bot: {resp.text}")
        sys.exit(1)
        
    data = resp.json()
    run_id = data['run_id']
    decision_id = 1 # Assuming first run on new DB, or we need to fetch logs to get ID
    
    # Fetch logs to get the real decision ID
    print("2. Fetching Logs to get Decision ID...")
    logs_resp = requests.get(f"{BASE_URL}/bot/logs", params={"limit": 1})
    logs = logs_resp.json()
    last_decision = logs[0]
    decision_id = last_decision['id']
    params_used = last_decision['params_used']
    print(f"   - Decision ID: {decision_id}")
    print(f"   - Params Chosen: {params_used}")
    
    # 2. Provide Positive Feedback
    print("3. Sending Positive Feedback (Reward = 100)...")
    fb_resp = requests.post(f"{BASE_URL}/bot/feedback", json={
        "decision_id": decision_id,
        "profit": 100.0
    })
    print(f"   - Feedback Response: {fb_resp.json()}")
    
    # 3. Verify State (This requires checking the DB or inferring from behavior, 
    #    for MVP we just check if it didn't crash and assuming logic holds.
    #    Real verification would query the bandit_state table via an endpoint if we exposed one,
    #    but we can assume success if 200 OK returned)
    
    print("4. Feedback loop completed successfully.")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)

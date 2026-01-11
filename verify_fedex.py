import requests
import json
from credential_manager import CredentialManager
from fedex_mapper import FedExMapper

def run_system_check():
    print("--- STARTING ARCHITECTURE VERIFICATION ---")
    
    # ---------------------------------------------------------
    # PHASE 1: BUY-SIDE LIQUIDITY (Authentication & Data Ingestion)
    # ---------------------------------------------------------
    try:
        # Initialize the Auth Service
        auth = CredentialManager()
        token = auth.get_token()
        print(f"[Pass] Authentication Service initialized.")
        print(f"[Pass] Token acquired: {token[:15]}...") 
    except Exception as e:
        print(f"[Fail] Authentication failed: {e}")
        return

    # Define the Test Payload (Mock Tracking Number for Sandbox)
    MOCK_TRACKING_NUMBER = "123456789012"
    url = f"{auth.base_url}/track/v1/trackingnumbers"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-locale": "en_US",
        "x-customer-transaction-id": "ARCH_TEST_001"
    }
    
    payload = {
        "includeDetailedScans": True,
        "trackingInfo": [
            {
                "trackingNumberInfo": {
                    "trackingNumber": MOCK_TRACKING_NUMBER
                }
            }
        ]
    }

    print(f"\n[Architect] Sending request for tracking number: {MOCK_TRACKING_NUMBER}...")
    
    raw_data = None
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        raw_data = response.json()
        print("[Pass] Raw Carrier Data Received.")
        
    except requests.exceptions.HTTPError as err:
        print(f"\n[Fail] HTTP Error: {err}")
        print(f"Response Body: {response.text}")
        return

    # ---------------------------------------------------------
    # PHASE 2: SELL-SIDE LIQUIDITY (Normalization & Standardization)
    # ---------------------------------------------------------
    print("\n--- NORMALIZATION PHASE ---")
    
    if raw_data:
        # Convert Raw FedEx JSON -> UnifiedEvent Object
        unified_event = FedExMapper.parse_tracking_response(raw_data)
        
        if unified_event:
            print("[Pass] Data Normalized Successfully. Final Output:")
            print("------------------------------------------------")
            # Convert the object to a dictionary for pretty printing
            print(json.dumps(unified_event.to_dict(), indent=2))
            print("------------------------------------------------")
        else:
            print("[Fail] Mapping Logic returned None. Check JSON structure.")

if __name__ == "__main__":
    run_system_check()
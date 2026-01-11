import json
from ups_connector import UPSConnector

def run_ups_check():
    print("--- STARTING UPS VERIFICATION ---")
    
    # 1. UPS Specific Mock Number
    # '1Z...' is the standard format. 
    # UPS often uses 1Z12345E0205271688 for successful delivery tests in sandbox.
    MOCK_ASSET = "1Z12345E0205271688"
    
    try:
        bot = UPSConnector()
        event = bot.track_shipment(MOCK_ASSET)
        
        if event:
            print("\n[Pass] UPS Data Liquidity Secured & Normalized:")
            print(json.dumps(event.to_dict(), indent=2))
        else:
            print("\n[Fail] Data received but parsing failed.")
            
    except Exception as e:
        print(f"\n[Fail] Critical UPS Error: {e}")

if __name__ == "__main__":
    run_ups_check()
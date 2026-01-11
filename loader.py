import csv
import requests
import time
from datetime import datetime, timedelta
import random
import json

# CONFIGURATION
API_URL = "http://127.0.0.1:8000/ingest/shipment"
CSV_FILE = "audit_ledger.csv"

def normalize_carrier(raw_val):
    """Enforces Sovereign Ledger naming conventions."""
    if not raw_val: return "FedEx"
    val = raw_val.strip().upper()
    if "FEDEX" in val: return "FedEx"
    if "UPS" in val: return "UPS"
    return "FedEx"

def replay_history():
    print(f"🚀 [INIT] Starting Historical Replay from {CSV_FILE}...")
    
    try:
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # --- HANDLE EMPTY CSV ---
            if not rows:
                print("⚠️ CSV is empty! Creating a dummy test record.")
                rows = [{
                    "tracking_number": f"TEST-{random.randint(10000,99999)}",
                    "carrier": "FedEx",
                    "service_type": "Priority Overnight",
                    "amount": "45.50"
                }]

            total = len(rows)
            print(f"📊 [DATA] Found {total} records to ingest.")
            
            for i, row in enumerate(rows):
                try:
                    # SIMULATE MISSING DATA
                    now = datetime.now()
                    
                    # Safe Float Conversion
                    raw_amount = row.get('amount', '18.50')
                    try:
                        charge = float(raw_amount.replace('$','').replace(',',''))
                    except:
                        charge = 18.50

                    # --- BUILD PAYLOAD ---
                    payload = {
                        "tracking_number": row.get('tracking_number', f"LEGACY-{random.randint(1000,9999)}"),
                        "carrier": normalize_carrier(row.get('carrier', 'FedEx')),
                        "service_type": row.get('service_type', 'Ground'),
                        "total_charged": charge,
                        "contract_rate": 14.00,
                        "shipped_at": (now - timedelta(days=3)).isoformat(),
                        "promised_delivery": (now - timedelta(days=1)).isoformat(),
                        "delivery_ts": (now - timedelta(hours=2)).isoformat(),
                        "raw_metadata": row
                    }

                    response = requests.post(API_URL, json=payload)
                    
                    if response.status_code == 200:
                        data = response.json()
                        # CRITICAL FIX: Convert string response to float before comparing
                        leakage = float(data['leakage_found'])
                        status_icon = "💰" if leakage > 0 else "✅"
                        
                        print(f"{status_icon} [{i+1}/{total}] Ingested: {payload['tracking_number']} | Leakage: ${leakage:.2f}")
                    else:
                        print(f"❌ [{i+1}/{total}] Failed: {response.text}")
                        
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                    
                time.sleep(0.1)

    except FileNotFoundError:
        print(f"❌ Error: {CSV_FILE} not found.")

if __name__ == "__main__":
    replay_history()
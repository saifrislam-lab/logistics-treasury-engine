import pdfplumber
import re
import requests
import json
import time
from datetime import datetime, timedelta

# ==================================================
# 🧠 CARRIER ALPHA: PDF MINING AGENT v3.3 (CONTEXT AWARE)
# ==================================================

API_URL = "http://127.0.0.1:8000/ingest/shipment"

class CarrierIngestor:
    def __init__(self):
        # CALIBRATED REGEX
        self.patterns = {
            # Tracking: 1Z (UPS) or 12-15 digits (FedEx)
            'tracking': r'\b1Z[A-Z0-9]{7,16}\b|\b\d{12,15}\b',
            'service': r'(Priority|Standard|Ground|Overnight|Express|Saver)',
            # Weight: Captures "12.5 lbs" or "4.0 KGS" (Case insensitive)
            'weight': r'(\d+(?:\.\d+)?)\s*(lbs|kgs|lb|kg)',
            'amount': r'\$\d+\.\d{2}',
            # ZIP: Captures standard US 5-digit or 5-4 format
            'zip': r'\b\d{5}(?:-\d{4})?\b'
        }

    def parse_and_push(self, pdf_path):
        print(f"🔄 [MINER] Extracting Liquidity & Context from: {pdf_path}...")
        
        detected_rows = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if not text: continue

                    lines = text.split('\n')
                    for line in lines:
                        processed_row = self._extract_alpha_from_line(line)
                        if processed_row:
                            detected_rows.append(processed_row)

            if detected_rows:
                print(f"🚀 [TRANSMIT] Sending {len(detected_rows)} artifacts to Treasury Engine...")
                self._transmit_to_api(detected_rows)
            else:
                print("❌ [MINER] No valid shipment rows found.")

        except FileNotFoundError:
            print(f"❌ Error: File {pdf_path} not found.")

    def _extract_alpha_from_line(self, line):
        # 1. Find Tracking Number (The Anchor)
        track_match = re.search(self.patterns['tracking'], line)
        if not track_match:
            return None
        
        tracking_number = track_match.group(0)

        # 2. SMART ROUTING
        if tracking_number.startswith("1Z"):
            carrier = "UPS"
        else:
            carrier = "FedEx"

        # 3. Find Price
        amounts = re.findall(self.patterns['amount'], line)
        if not amounts:
            return None # Skip if no cost attached (unbillable)
        net_charge = float(amounts[-1].replace('$', '').replace(',', ''))

        # 4. Find Service
        service = re.search(self.patterns['service'], line, re.I)
        service_type = service.group(0) if service else "Standard"

        # --- NEW LOGIC START ---
        
        # 5. Find Weight
        # Returns tuple like ('12.5', 'lbs')
        weight_match = re.search(self.patterns['weight'], line, re.I)
        if weight_match:
            weight_val = float(weight_match.group(1))
            weight_unit = weight_match.group(2).upper()
        else:
            weight_val = 1.0 # Default fallback
            weight_unit = "LBS"

        # 6. Find ZIP Codes (Origin vs Dest)
        # Logic: Invoices usually list Origin first, then Dest, OR just Dest.
        zips = re.findall(self.patterns['zip'], line)
        
        origin_zip = None
        dest_zip = None

        if len(zips) >= 2:
            origin_zip = zips[0]
            dest_zip = zips[1]
        elif len(zips) == 1:
            dest_zip = zips[0] # Assume single ZIP is always destination
            origin_zip = "DEFAULT_WH" # Placeholder for your main warehouse ZIP

        # --- NEW LOGIC END ---

        return {
            "tracking_number": tracking_number,
            "carrier": carrier, 
            "service_type": service_type,
            "total_charged": net_charge,
            "weight_val": weight_val,
            "weight_unit": weight_unit,
            "origin_zip": origin_zip,
            "dest_zip": dest_zip,
            "raw_line": line
        }

    def _transmit_to_api(self, rows):
        success_count = 0
        
        for i, row in enumerate(rows):
            now = datetime.now()
            
            payload = {
                "tracking_number": row['tracking_number'],
                "carrier": row['carrier'],
                "service_type": row['service_type'],
                "total_charged": row['total_charged'],
                
                # NEW FIELDS FOR PHASE 2
                "weight_value": row['weight_val'],
                "weight_unit": row['weight_unit'],
                "origin_zip": row['origin_zip'],
                "destination_zip": row['dest_zip'],
                
                "contract_rate": 14.00, 
                "shipped_at": (now - timedelta(days=3)).isoformat(),
                "promised_delivery": (now - timedelta(days=1)).isoformat(),
                "delivery_ts": (now - timedelta(hours=2)).isoformat(),
                "raw_metadata": {"source_line": row['raw_line']}
            }

            try:
                response = requests.post(API_URL, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    leakage = float(data.get('leakage_found', 0))
                    icon = "💰" if leakage > 0 else "✅"
                    print(f"{icon} [{row['carrier']}] {row['tracking_number']} | {row['dest_zip']} | {row['weight_val']}{row['weight_unit']} | ${row['total_charged']}")
                    success_count += 1
                else:
                    print(f"⚠️ [{i+1}] API Reject: {response.text}")
            
            except Exception as e:
                print(f"❌ Connection Error: {e}")
            
            time.sleep(0.05)

        print("="*40)
        print(f"🏁 MINING COMPLETE. {success_count} Artifacts Secured.")

if __name__ == "__main__":
    engine = CarrierIngestor()
    target_file = "fedex_invoice_sample.pdf" 
    engine.parse_and_push(target_file)
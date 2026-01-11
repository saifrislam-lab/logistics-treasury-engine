import csv
import os
from datetime import datetime
from pathlib import Path

# Set the path for our Treasury Ledger
LEDGER_FILE = Path(__file__).resolve().parent.parent.parent / 'audit_ledger.csv'

class AuditEngine:
    @staticmethod
    def log_event(data: dict):
        """
        Appends a standardized tracking event to the institutional ledger.
        """
        file_exists = LEDGER_FILE.exists()
        
        # Institutional fields for the ledger
        fieldnames = [
            "timestamp", 
            "carrier", 
            "tracking_number", 
            "status", 
            "description"
        ]

        try:
            with open(LEDGER_FILE, mode='a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header if this is a new ledger
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow({
                    "timestamp": data.get("timestamp"),
                    "carrier": data.get("carrier"),
                    "tracking_number": data.get("tracking_number"),
                    "status": data.get("status"),
                    "description": data.get("description")
                })
        except Exception as e:
            print(f"[Audit Engine Error] Failed to write to ledger: {e}")
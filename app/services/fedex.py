import os
import requests
import time
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import dateutil.parser

# Institutional Path Management
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class FedExService:
    def __init__(self):
        self.api_key = os.getenv("FEDEX_API_KEY")
        self.secret_key = os.getenv("FEDEX_SECRET_KEY")
        self.base_url = os.getenv("FEDEX_BASE_URL")
        self._token = None
        self._expires_at = 0

    def _get_token(self):
        """Secures OAuth liquidity from FedEx."""
        if self._token and time.time() < self._expires_at:
            return self._token
        
        url = f"{self.base_url}/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        try:
            resp = requests.post(url, data=payload)
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            self._expires_at = time.time() + data["expires_in"] - 60
            return self._token
        except Exception as e:
            print(f"⚠️ [AUTH FAIL] Could not get FedEx Token: {e}")
            return None

    def track(self, tracking_number: str):
        """Fetches LIVE asset data from FedEx (The Spot Price)."""
        try:
            token = self._get_token()
            if not token:
                return None

            url = f"{self.base_url}/track/v1/trackingnumbers"
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            payload = {
                "includeDetailedScans": True, 
                "trackingInfo": [{"trackingNumberInfo": {"trackingNumber": tracking_number}}]
            }
            
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                print(f"⚠️ FedEx API Error: {response.status_code} | {response.text}")
                return None
            
            data = response.json()
            track_result = data["output"]["completeTrackResults"][0]["trackResults"][0]
            latest = track_result["latestStatusDetail"]
            
            # CRITICAL: Extract the REAL event time.
            # We prioritize 'date' (usually the event timestamp)
            raw_ts = latest.get("date") or latest.get("time") 
            
            # Fallback to scan history if top-level is vague
            if not raw_ts:
                try:
                    raw_ts = track_result["scanEvents"][0]["date"]
                except:
                    # If we truly can't find a time, we default to NOW but flag it
                    print(f"⚠️ No Timestamp found for {tracking_number}. Using System Time.")
                    raw_ts = datetime.now().isoformat()

            return {
                "tracking_number": tracking_number,
                "carrier": "FEDEX",
                "status": latest.get("statusByLocale", "Unknown"), 
                "code": latest.get("code"),
                "timestamp": raw_ts # <--- The Real Spot Price
            }
        except Exception as e:
            print(f"⚠️ FedEx Service Failure: {e}")
            return None
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

class UPSService:
    def __init__(self):
        self.client_id = os.getenv("UPS_CLIENT_ID")
        self.client_secret = os.getenv("UPS_CLIENT_SECRET")
        self.base_url = os.getenv("UPS_BASE_URL", "https://onlinetools.ups.com") 
        self._token = None
        self._expires_at = 0

    def _get_token(self):
        """Secures OAuth liquidity from UPS."""
        if self._token and time.time() < self._expires_at:
            return self._token
        
        url = f"{self.base_url}/security/v1/oauth/token"
        payload = {"grant_type": "client_credentials"}
        
        # UPS requires Basic Auth (Client ID:Secret)
        try:
            resp = requests.post(url, data=payload, auth=(self.client_id, self.client_secret))
            resp.raise_for_status()
            data = resp.json()
            
            self._token = data["access_token"]
            expires_in = int(data.get("expires_in", 3600))
            self._expires_at = time.time() + expires_in - 60
            return self._token
        except Exception as e:
            print(f"⚠️ [UPS AUTH FAIL] Could not get Token: {e}")
            return None

    def track(self, tracking_number: str):
        """Fetches LIVE asset data from UPS (The Spot Price)."""
        try:
            token = self._get_token()
            if not token:
                return None

            url = f"{self.base_url}/api/track/v1/details/{tracking_number}"
            headers = {
                "Authorization": f"Bearer {token}", 
                "transId": str(int(time.time())), 
                "transactionSrc": "CarrierAlpha"
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"⚠️ UPS API Error: {response.status_code} | {response.text}")
                return None
            
            data = response.json()
            
            # --- DEEP SEARCH ALGORITHM ---
            try:
                pkg = data["trackResponse"]["shipment"][0]["package"][0]
                activity = pkg["activity"][0] # The latest event
                
                # UPS splits Date (YYYYMMDD) and Time (HHMMSS)
                date_str = activity["date"]
                time_str = activity["time"]
                full_str = f"{date_str} {time_str}"
                
                # Parse to robust ISO format
                real_ts = datetime.strptime(full_str, "%Y%m%d %H%M%S").isoformat()
                status_desc = activity["status"]["description"]
                
                return {
                    "tracking_number": tracking_number,
                    "carrier": "UPS",
                    "status": status_desc,
                    "timestamp": real_ts # <--- The Real Spot Price
                }

            except (KeyError, IndexError) as e:
                print(f"⚠️ UPS Parse Error (Structure Mismatch): {e}")
                return None

        except Exception as e:
            print(f"⚠️ UPS Service Failure: {e}")
            return None
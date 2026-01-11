import os
import requests
import base64
import json
from datetime import datetime
from dotenv import load_dotenv
from models import UnifiedEvent

load_dotenv()

class UPSConnector:
    def __init__(self):
        self.client_id = os.getenv("UPS_CLIENT_ID")
        self.client_secret = os.getenv("UPS_CLIENT_SECRET")
        self.account_number = os.getenv("UPS_ACCOUNT_NUMBER")
        self.base_url = os.getenv("UPS_BASE_URL")
        self._token = None

    def _get_auth_token(self):
        url = f"{self.base_url}/security/v1/oauth/token"
        creds = f"{self.client_id}:{self.client_secret}"
        encoded_creds = base64.b64encode(creds.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_creds}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        payload = {"grant_type": "client_credentials"}
        
        print(f"[UPS] Requesting Token...")
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        self._token = response.json()["access_token"]
        return self._token

    def normalize_ups_status(self, code: str) -> str:
        mapping = {
            "M": "PRE_TRANSIT",
            "I": "IN_TRANSIT",
            "P": "IN_TRANSIT",
            "D": "DELIVERED",
            "X": "EXCEPTION",
            "RS": "RETURN_TO_SENDER"
        }
        return mapping.get(code, "UNKNOWN")

    def track_shipment(self, tracking_number: str):
        if not self._token:
            self._get_auth_token()

        # NOTE: Updated endpoint to v2 or specific wrapper if needed, 
        # but sticking to standard structure for diagnosis.
        url = f"{self.base_url}/api/track/v1/details/{tracking_number}"
        
        headers = {
            "Authorization": f"Bearer {self._token}",
            "transId": "ISOL_TEST_001",
            "transactionSrc": "testing"
        }
        
        params = {"locale": "en_US"}

        print(f"[UPS] Tracking Asset: {tracking_number}...")
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return self._parse_response(response.json(), tracking_number)

    def _parse_response(self, raw_data, tracking_number):
        try:
            # --- DEBUG BLOCK ---
            # We suspect the structure is slightly different.
            # This print confirms we got data and shows us the structure.
            # -------------------
            # print("DEBUG: Raw UPS Data Follows:")
            # print(json.dumps(raw_data, indent=2))
            
            # Navigating the UPS Response
            pkg = raw_data["trackResponse"]["shipment"][0]["package"][0]
            
            # Grab the latest activity
            activity = pkg["activity"][0] 
            
            # SAFE PARSING: Use .get() to avoid crashing if fields are missing
            status_obj = activity.get("status", {})
            status_code = status_obj.get("code", "UNKNOWN")
            status_type = status_obj.get("type", "UNKNOWN") # Sometimes UPS uses 'type'
            status_desc = status_obj.get("description", "No description")
            
            # Fallback: if 'code' is empty, try using 'type'
            final_code = status_code if status_code != "UNKNOWN" else status_type
            
            loc = activity.get("location", {}).get("address", {})
            city = loc.get("city", "Unknown")
            state = loc.get("stateProvince", "")
            
            return UnifiedEvent(
                tracking_number=tracking_number,
                carrier="UPS",
                status=self.normalize_ups_status(final_code),
                description=status_desc,
                timestamp=datetime.now().isoformat(),
                location=f"{city}, {state}".strip(", "),
                raw_status_code=final_code
            )
        except Exception as e:
            print(f"[UPS] Parsing Error: {e}")
            print("--- CRITICAL DUMP ---")
            print(json.dumps(raw_data, indent=2))
            return None
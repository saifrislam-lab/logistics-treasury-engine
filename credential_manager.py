import os
import time
import requests
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

class CredentialManager:
    def __init__(self):
        # Load configuration from environment
        self.api_key = os.getenv("FEDEX_API_KEY")
        self.secret_key = os.getenv("FEDEX_SECRET_KEY")
        self.base_url = os.getenv("FEDEX_BASE_URL")
        
        # Internal state for the token
        self._token = None
        self._expires_at = 0

    def get_token(self):
        """
        Returns a valid access token. 
        Automatically refreshes the token if it has expired.
        """
        if self._should_refresh():
            print("[Architect] Token expired or missing. Refreshing...")
            self._refresh_token()
        return self._token

    def _should_refresh(self):
        """Checks if the current token is expired or about to expire."""
        # Refresh if we have no token OR if we are within 5 minutes (300s) of expiry
        return self._token is None or time.time() >= (self._expires_at - 300)

    def _refresh_token(self):
        """Performs the OAuth 2.0 handshake with FedEx."""
        url = f"{self.base_url}/oauth/token"
        
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            response = requests.post(url, data=payload, headers=headers)
            response.raise_for_status() # strict error checking
            
            data = response.json()
            self._token = data["access_token"]
            # Set expiration time (current time + lifespan of token)
            self._expires_at = time.time() + data["expires_in"]
            
        except Exception as e:
            print(f"[Architect] CRITICAL AUTH FAILURE: {e}")
            raise e
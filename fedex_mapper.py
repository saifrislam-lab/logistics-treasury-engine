from models import UnifiedEvent
from datetime import datetime

class FedExMapper:
    @staticmethod
    def normalize_status(fedex_code: str) -> str:
        """
        Maps FedEx-specific codes to our Unified Standard.
        """
        mapping = {
            "OC": "PRE_TRANSIT",      # Order Created
            "PU": "IN_TRANSIT",       # Picked Up
            "DP": "IN_TRANSIT",       # Departed
            "AR": "IN_TRANSIT",       # Arrived
            "IT": "IN_TRANSIT",       # In Transit
            "OD": "OUT_FOR_DELIVERY", # On Delivery
            "DL": "DELIVERED",        # Delivered
            "HL": "EXCEPTION",        # Hold at Location (Action Required)
            "SE": "EXCEPTION",        # Shipment Exception
        }
        return mapping.get(fedex_code, "UNKNOWN")

    @staticmethod
    def parse_tracking_response(raw_json: dict) -> UnifiedEvent:
        """
        Extracts key data from the complex FedEx Payload.
        """
        try:
            # 1. Navigate to the core result object
            complete_result = raw_json["output"]["completeTrackResults"][0]
            track_result = complete_result["trackResults"][0]
            
            # 2. Extract Basic Info
            tracking_number = track_result["trackingNumberInfo"]["trackingNumber"]
            
            # 3. Extract Latest Status
            latest_status = track_result["latestStatusDetail"]
            raw_code = latest_status.get("code")
            description = latest_status.get("description")
            
            # 4. Extract Location
            loc = latest_status.get("scanLocation", {})
            city = loc.get("city", "Unknown")
            state = loc.get("stateOrProvinceCode", "")
            location_str = f"{city}, {state}".strip(", ")

            # 5. Build the Unified Object
            return UnifiedEvent(
                tracking_number=tracking_number,
                carrier="FEDEX",
                status=FedExMapper.normalize_status(raw_code),
                description=description,
                timestamp=datetime.now().isoformat(),
                location=location_str,
                raw_status_code=raw_code
            )
            
        except (KeyError, IndexError) as e:
            print(f"[Mapper] Error parsing FedEx JSON: {e}")
            return None
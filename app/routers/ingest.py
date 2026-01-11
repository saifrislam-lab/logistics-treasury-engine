from fastapi import APIRouter, HTTPException, Depends
from decimal import Decimal
from datetime import datetime
import dateutil.parser 

from app.schemas import ShipmentIngest, AuditResponse
from app.services.supabase_client import get_supabase
from app.services.fedex import FedExService
from app.services.ups import UPSService
from supabase import Client

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

# INSTANTIATE INSTITUTIONAL ENGINES
fedex_engine = FedExService() 
ups_engine = UPSService()

# MODULE 2.3: DETERMINISTIC EXCEPTION TRIGGERS
# These keywords identify events that void the Guaranteed Service Refund (GSR)
EXCUSABLE_KEYWORDS = [
    "WEATHER", "NATURAL DISASTER", "EMERGENCY", "FORCE MAJEURE", 
    "STRIKE", "NATIONAL EMERGENCY", "SECURITY DELAY", "GOVERNMENT",
    "ACT OF GOD", "CLOSED DUE TO"
]

@router.post("/shipment", response_model=AuditResponse)
def ingest_and_audit(shipment: ShipmentIngest, db: Client = Depends(get_supabase)):
    try:
        # --- 0. LIVE SPOT PRICE & EXCEPTION CHECK ---
        live_data = None
        exception_found = False
        failure_reason = "Late Delivery (GSR)"
        
        carrier_clean = shipment.carrier.strip().upper()

        # FETCH LIVE TAPE
        if "FEDEX" in carrier_clean:
            print(f"📡 [FEDEX CHECK] Polling Live Tape for {shipment.tracking_number}...")
            live_data = fedex_engine.track(shipment.tracking_number)
            
        elif "UPS" in carrier_clean:
            print(f"📡 [UPS CHECK] Polling Live Tape for {shipment.tracking_number}...")
            live_data = ups_engine.track(shipment.tracking_number)

        # PROCESS THE LIVE TRUTH
        if live_data:
            try:
                # 0.1 Update Delivery Timestamp from Live Tape
                real_delivery = dateutil.parser.parse(live_data['timestamp'])
                shipment.delivery_ts = real_delivery.replace(tzinfo=None) if real_delivery.tzinfo else real_delivery
                print(f"✅ [VERIFIED] Live Delivery Time: {shipment.delivery_ts}")

                # 0.2 SCAN FOR EXCEPTIONS (Module 2.3)
                # We check status and description to see if the carrier has "covered" themselves
                status_text = f"{live_data.get('status', '')} {live_data.get('description', '')}".upper()
                for kw in EXCUSABLE_KEYWORDS:
                    if kw in status_text:
                        exception_found = True
                        failure_reason = f"Excusable Delay: {kw}"
                        print(f"🛑 [EXCEPTION DETECTED] {shipment.tracking_number} flagged for {kw}")
                        break

            except Exception as e:
                print(f"⚠️ Date Parse Warning: {e}. Falling back to provided timestamp.")
        else:
             if "FEDEX" in carrier_clean or "UPS" in carrier_clean:
                print("⚠️ [LIVE FAIL] Could not verify with Carrier. Defaulting to provided data.")

        # --- 1. AUDIT LOGIC (Staff Engineer Standard) ---
        promised = shipment.promised_delivery.replace(tzinfo=None) if shipment.promised_delivery.tzinfo else shipment.promised_delivery
        actual = shipment.delivery_ts.replace(tzinfo=None) if shipment.delivery_ts.tzinfo else shipment.delivery_ts

        is_late = actual > promised
        
        # ELIGIBILITY: Must be late AND not have an excusable exception
        is_eligible = is_late and not exception_found
        
        # Financial Spread Calculation
        alpha_price = Decimal("0.00") if is_eligible else shipment.contract_rate
        spread = shipment.total_charged - alpha_price

        # --- 2. SOVEREIGN LEDGER WRITE ---
        safe_json_data = shipment.model_dump(mode='json')
        ship_data = {
            "tracking_number": shipment.tracking_number,
            "carrier": shipment.carrier,
            "service_type": shipment.service_type,
            "shipped_at": shipment.shipped_at.isoformat(),
            "promised_delivery": shipment.promised_delivery.isoformat(),
            "actual_delivery": shipment.delivery_ts.isoformat(),
            "raw_json_data": safe_json_data 
        }
        
        ship_res = db.table("shipments").upsert(ship_data, on_conflict="tracking_number").execute()
        shipment_id = ship_res.data[0]['id']

        # --- 3. AUDIT RESULT WRITE ---
        # We record the specific rule used to provide full explainability
        audit_res = db.table("audit_results").insert({
            "shipment_id": shipment_id,
            "is_eligible": is_eligible,
            "variance_amount": float(spread),
            "failure_reason": failure_reason if is_late else None,
            "rule_id": "RULE_2.3_EXCEPTION" if exception_found else "RULE_2.2_LATE"
        }).execute()

        # --- 4. CLAIMS ---
        claim_status = "SKIPPED"
        if is_eligible:
            db.table("claims").insert({
                "shipment_id": shipment_id,
                "audit_id": audit_res.data[0]['id'],
                "status": "DRAFT",
                "claim_amount": float(spread)
            }).execute()
            claim_status = "DRAFT_CREATED"

        return AuditResponse(
            status="success",
            tracking_number=shipment.tracking_number,
            leakage_found=spread,
            claim_status=claim_status
        )

    except Exception as e:
        print(f"ERROR in /ingest/shipment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
from fastapi import APIRouter, HTTPException, Depends
from decimal import Decimal
from datetime import datetime, timezone
import dateutil.parser

from app.schemas import ShipmentIngest, AuditResponse
from app.services.supabase_client import get_supabase
from app.services.fedex import FedExService
from app.services.ups import UPSService
from supabase import Client

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

# INSTANTIATE ENGINES
fedex_engine = FedExService()
ups_engine = UPSService()

# Deterministic exception triggers (void GSR)
EXCUSABLE_KEYWORDS = [
    "WEATHER", "NATURAL DISASTER", "EMERGENCY", "FORCE MAJEURE",
    "STRIKE", "NATIONAL EMERGENCY", "SECURITY DELAY", "GOVERNMENT",
    "ACT OF GOD", "CLOSED DUE TO"
]

def _to_utc(dt: datetime) -> datetime:
    """
    Convert a datetime to UTC for timestamptz storage.
    - If timezone-aware: convert to UTC.
    - If naive: assume UTC (v1). (Optionally lower confidence later.)
    """
    if dt is None:
        raise ValueError("Datetime cannot be None")
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _get_single(rowset):
    return rowset[0] if rowset else None

def _normalize_carrier(carrier: str) -> str:
    c = (carrier or "").strip().upper()
    # Accept common variants if they sneak in
    if c in ["FEDEX", "FEDX", "FDX"]:
        return "FEDEX"
    if c in ["UPS", "UNITED PARCEL SERVICE"]:
        return "UPS"
    return c

def _normalize_service_type(service_type: str) -> str:
    """
    v1 normalization: uppercase + trim + collapse whitespace.
    Keep it simple and deterministic.
    """
    if not service_type:
        return ""
    return " ".join(service_type.strip().upper().split())

def _is_service_guaranteed(db: Client, carrier: str, service_type_norm: str) -> bool:
    """
    Lookup against service_commitments.
    v1 rule: if we cannot find a matching row, treat as NON_GUARANTEED.
    (Fail-closed prevents false positives.)
    """
    if not service_type_norm:
        return False

    resp = (
        db.table("service_commitments")
        .select("guaranteed")
        .eq("carrier", carrier)
        .eq("service_type", service_type_norm)
        .is_("valid_to", "null")  # current row if valid_to is null
        .order("valid_from", desc=True)
        .limit(1)
        .execute()
    )

    row = _get_single(resp.data)
    return bool(row["guaranteed"]) if row else False

def _get_shipment_by_natural_key(db: Client, carrier: str, tracking_number: str):
    resp = (
        db.table("shipments")
        .select("*")
        .eq("carrier", carrier)
        .eq("tracking_number", tracking_number)
        .limit(1)
        .execute()
    )
    return _get_single(resp.data)

def _upsert_shipment(db: Client, carrier: str, tracking_number: str, fields: dict):
    """
    Idempotent shipment upsert keyed by (carrier, tracking_number).
    """
    existing = _get_shipment_by_natural_key(db, carrier, tracking_number)
    payload = {"carrier": carrier, "tracking_number": tracking_number, **fields}

    if existing:
        resp = db.table("shipments").update(payload).eq("id", existing["id"]).execute()
        return resp.data[0]
    else:
        resp = db.table("shipments").insert(payload).execute()
        return resp.data[0]

def _get_audit_by_shipment_id(db: Client, shipment_id: str):
    resp = db.table("audit_results").select("*").eq("shipment_id", shipment_id).limit(1).execute()
    return _get_single(resp.data)

def _upsert_audit_result(db: Client, shipment_id: str, fields: dict):
    """
    One audit_result per shipment_id (DB unique constraint enforces this).
    """
    existing = _get_audit_by_shipment_id(db, shipment_id)
    payload = {"shipment_id": shipment_id, **fields}

    if existing:
        resp = db.table("audit_results").update(payload).eq("id", existing["id"]).execute()
        return resp.data[0]
    else:
        resp = db.table("audit_results").insert(payload).execute()
        return resp.data[0]

def _get_claim_by_shipment_id(db: Client, shipment_id: str):
    resp = db.table("claims").select("*").eq("shipment_id", shipment_id).limit(1).execute()
    return _get_single(resp.data)

def _upsert_claim(db: Client, shipment_id: str, audit_id: str, fields: dict):
    """
    One claim per shipment_id (DB unique constraint enforces this).
    """
    existing = _get_claim_by_shipment_id(db, shipment_id)
    payload = {"shipment_id": shipment_id, "audit_id": audit_id, **fields}

    if existing:
        resp = db.table("claims").update(payload).eq("id", existing["id"]).execute()
        return resp.data[0]
    else:
        resp = db.table("claims").insert(payload).execute()
        return resp.data[0]

@router.post("/shipment", response_model=AuditResponse)
def ingest_and_audit(shipment: ShipmentIngest, db: Client = Depends(get_supabase)):
    """
    Carrier Alpha v1 ingestion:
    - Idempotent on (carrier, tracking_number)
    - Deterministic decision ledger (audit_results)
    - Claim lifecycle (claims) created only when eligible
    - Service guarantee eligibility driven by service_commitments table
    """
    try:
        # -----------------------------
        # 0) Canonical inputs
        # -----------------------------
        carrier = _normalize_carrier(shipment.carrier)
        if carrier not in ["FEDEX", "UPS"]:
            raise HTTPException(status_code=400, detail=f"Unsupported carrier: {shipment.carrier}")

        tracking = shipment.tracking_number.strip()
        service_norm = _normalize_service_type(shipment.service_type)

        # -----------------------------
        # 1) Live verification (optional)
        # -----------------------------
        live_data = None
        exception_found = False
        failure_reason = None

        if carrier == "FEDEX":
            print(f"📡 [FEDEX] Live track: {tracking}")
            live_data = fedex_engine.track(tracking)
        elif carrier == "UPS":
            print(f"📡 [UPS] Live track: {tracking}")
            live_data = ups_engine.track(tracking)

        # Prefer live timestamp if available, else use provided
        actual_dt = shipment.delivery_ts
        if live_data and live_data.get("timestamp"):
            try:
                parsed = dateutil.parser.parse(live_data["timestamp"])
                actual_dt = parsed
                print(f"✅ [LIVE TS] Using carrier timestamp: {parsed}")
            except Exception as e:
                print(f"⚠️ [LIVE TS PARSE] {e}. Using provided delivery_ts.")

        # Exception scan (status + description if present)
        if live_data:
            status_text = f"{live_data.get('status', '')} {live_data.get('description', '')}".upper()
            for kw in EXCUSABLE_KEYWORDS:
                if kw in status_text:
                    exception_found = True
                    failure_reason = f"Excusable Delay: {kw}"
                    print(f"🛑 [EXCEPTION] {tracking} flagged for {kw}")
                    break

        # -----------------------------
        # 2) Deterministic audit (v1)
        # -----------------------------
        promised_utc = _to_utc(shipment.promised_delivery)
        actual_utc = _to_utc(actual_dt)

        is_late = actual_utc > promised_utc

        # Service guarantee lookup (DB-driven)
        is_guaranteed = _is_service_guaranteed(db, carrier, service_norm)

        # Eligibility: must be late, guaranteed service, and not excusable
        is_eligible = bool(is_late and is_guaranteed and not exception_found)

        # v1 economics: refundable_amount = total_charged if eligible else 0
        refundable_amount = shipment.total_charged if is_eligible else Decimal("0.00")

        # Decision narrative
        if not is_guaranteed:
            # Fail-closed: non-guaranteed unless explicitly listed
            failure_reason = "Non-guaranteed service" if failure_reason is None else failure_reason
        elif is_late and failure_reason is None:
            failure_reason = "Late Delivery (GSR)"
        elif not is_late:
            failure_reason = None  # no issue if on-time

        # Rule id (minimal explainability)
        if exception_found:
            rule_id = "RULE_EXCEPTION_KEYWORD"
        elif not is_guaranteed:
            rule_id = "RULE_SERVICE_NOT_GUARANTEED"
        else:
            rule_id = "RULE_LATE_DELIVERY"

        # -----------------------------
        # 3) Shipment upsert (canonical)
        # -----------------------------
        safe_json_data = shipment.model_dump(mode="json")

        ship_fields = {
            "service_type": service_norm if service_norm else shipment.service_type,
            "shipped_at": _to_utc(shipment.shipped_at).isoformat(),
            "promised_delivery": promised_utc.isoformat(),
            "actual_delivery": actual_utc.isoformat(),
            "total_charged": float(shipment.total_charged),
            "weight_lbs": float(shipment.weight_value) if getattr(shipment, "weight_value", None) is not None else None,
            "raw_json_data": safe_json_data,
        }

        ship_row = _upsert_shipment(db, carrier, tracking, ship_fields)
        shipment_id = ship_row["id"]

        # -----------------------------
        # 4) Audit upsert (one per shipment)
        # -----------------------------
        audit_fields = {
            "is_eligible": is_eligible,
            "variance_amount": float(refundable_amount),
            "failure_reason": failure_reason,
            "rule_id": rule_id,
            "audited_at": datetime.now(timezone.utc).isoformat(),
        }
        audit_row = _upsert_audit_result(db, shipment_id, audit_fields)
        audit_id = audit_row["id"]

        # -----------------------------
        # 5) Claim upsert (only if eligible)
        # -----------------------------
        claim_status = "SKIPPED"
        if is_eligible:
            claim_fields = {
                "status": "DRAFT",
                "claim_amount": float(refundable_amount),
                "reason": failure_reason or "Late Delivery (GSR)",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            _upsert_claim(db, shipment_id, audit_id, claim_fields)
            claim_status = "DRAFT"

        return AuditResponse(
            status="success",
            tracking_number=tracking,
            leakage_found=refundable_amount,
            claim_status=claim_status
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in /ingest/shipment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

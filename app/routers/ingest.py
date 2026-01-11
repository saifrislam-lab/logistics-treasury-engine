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

fedex_engine = FedExService()
ups_engine = UPSService()

EXCUSABLE_KEYWORDS = [
    "WEATHER", "NATURAL DISASTER", "EMERGENCY", "FORCE MAJEURE",
    "STRIKE", "NATIONAL EMERGENCY", "SECURITY DELAY", "GOVERNMENT",
    "ACT OF GOD", "CLOSED DUE TO"
]

AMBIGUOUS_TIME_WINDOW_MINUTES = 30  # deterministic fail-closed threshold

def _get_single(rowset):
    return rowset[0] if rowset else None

def _normalize_carrier(carrier: str) -> str:
    c = (carrier or "").strip().upper()
    if c in ["FEDEX", "FEDX", "FDX"]:
        return "FEDEX"
    if c in ["UPS", "UNITED PARCEL SERVICE"]:
        return "UPS"
    return c

def _normalize_service_type(service_type: str) -> str:
    if not service_type:
        return ""
    return " ".join(service_type.strip().upper().split())

def _to_utc_with_assumption(dt: datetime) -> tuple[datetime, str, float]:
    """
    Returns (utc_dt, timezone_assumption, confidence).
    - If tz-aware: convert to UTC, confidence 1.0
    - If naive: assume UTC, confidence 0.7
    """
    if dt is None:
        raise ValueError("Datetime cannot be None")

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc), "UTC_ASSUMED", 0.7

    return dt.astimezone(timezone.utc), "SOURCE_TZ", 1.0

def _is_service_guaranteed(db: Client, carrier: str, service_type_norm: str) -> bool:
    if not service_type_norm:
        return False

    resp = (
        db.table("service_commitments")
        .select("guaranteed")
        .eq("carrier", carrier)
        .eq("service_type", service_type_norm)
        .is_("valid_to", "null")
        .order("valid_from", desc=True)
        .limit(1)
        .execute()
    )
    row = _get_single(resp.data)
    return bool(row["guaranteed"]) if row else False

def _lookup_exception_rule(db: Client, carrier: str, code: str | None, text: str) -> tuple[bool, str | None, str | None]:
    """
    Deterministic exception evaluation:
    1) CODE rules (authoritative if present)
    2) KEYWORD rules (DB-driven)
    3) fallback keyword list (legacy)
    Returns: (exception_found, category, signal)
    """
    carrier = (carrier or "").strip().upper()
    text_u = (text or "").upper()
    code_u = (code or "").upper() if code else None

    # 1) CODE match
    if code_u:
        resp = (
            db.table("exception_rules")
            .select("excusable, category, match_value")
            .eq("carrier", carrier)
            .eq("match_type", "CODE")
            .eq("match_value", code_u)
            .limit(1)
            .execute()
        )
        row = _get_single(resp.data)
        if row and bool(row["excusable"]):
            return True, row.get("category"), f"CODE:{row.get('match_value')}"

    # 2) KEYWORD match (DB rules)
    resp_kw = (
        db.table("exception_rules")
        .select("excusable, category, match_value")
        .eq("carrier", carrier)
        .eq("match_type", "KEYWORD")
        .execute()
    )
    for r in (resp_kw.data or []):
        mv = (r.get("match_value") or "").upper()
        if mv and mv in text_u and bool(r.get("excusable")):
            return True, r.get("category"), f"KW:{mv}"

    # 3) fallback list (v1)
    for kw in EXCUSABLE_KEYWORDS:
        if kw in text_u:
            return True, "OTHER", f"KW_FALLBACK:{kw}"

    return False, None, None

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
    existing = _get_shipment_by_natural_key(db, carrier, tracking_number)
    payload = {"carrier": carrier, "tracking_number": tracking_number, **fields}
    if existing:
        resp = db.table("shipments").update(payload).eq("id", existing["id"]).execute()
        return resp.data[0]
    resp = db.table("shipments").insert(payload).execute()
    return resp.data[0]

def _get_audit_by_shipment_id(db: Client, shipment_id: str):
    resp = db.table("audit_results").select("*").eq("shipment_id", shipment_id).limit(1).execute()
    return _get_single(resp.data)

def _upsert_audit_result(db: Client, shipment_id: str, fields: dict):
    existing = _get_audit_by_shipment_id(db, shipment_id)
    payload = {"shipment_id": shipment_id, **fields}
    if existing:
        resp = db.table("audit_results").update(payload).eq("id", existing["id"]).execute()
        return resp.data[0]
    resp = db.table("audit_results").insert(payload).execute()
    return resp.data[0]

def _get_claim_by_shipment_id(db: Client, shipment_id: str):
    resp = db.table("claims").select("*").eq("shipment_id", shipment_id).limit(1).execute()
    return _get_single(resp.data)

def _upsert_claim(db: Client, shipment_id: str, audit_id: str, fields: dict):
    existing = _get_claim_by_shipment_id(db, shipment_id)
    payload = {"shipment_id": shipment_id, "audit_id": audit_id, **fields}
    if existing:
        resp = db.table("claims").update(payload).eq("id", existing["id"]).execute()
        return resp.data[0]
    resp = db.table("claims").insert(payload).execute()
    return resp.data[0]

@router.post("/shipment", response_model=AuditResponse)
def ingest_and_audit(shipment: ShipmentIngest, db: Client = Depends(get_supabase)):
    try:
        # 0) Canonical inputs
        carrier = _normalize_carrier(shipment.carrier)
        if carrier not in ["FEDEX", "UPS"]:
            raise HTTPException(status_code=400, detail=f"Unsupported carrier: {shipment.carrier}")

        tracking = shipment.tracking_number.strip()
        service_norm = _normalize_service_type(shipment.service_type)

        # 1) Live verification (optional)
        live_data = None
        live_exception_code = None
        live_exception_text = ""

        if carrier == "FEDEX":
            live_data = fedex_engine.track(tracking)
        elif carrier == "UPS":
            live_data = ups_engine.track(tracking)

        actual_dt = shipment.delivery_ts
        if live_data and live_data.get("timestamp"):
            try:
                actual_dt = dateutil.parser.parse(live_data["timestamp"])
            except Exception:
                pass

        # Use whatever structured fields are available (if adapters provide them)
        live_exception_code = (live_data.get("exception_code") if live_data else None)
        live_exception_text = f"{(live_data.get('status','') if live_data else '')} {(live_data.get('description','') if live_data else '')}"

        # 2) Time normalization with explicit assumption tracking (Caveat #1 fix)
        promised_utc, promised_tz_assumption, promised_conf = _to_utc_with_assumption(shipment.promised_delivery)
        actual_utc, actual_tz_assumption, actual_conf = _to_utc_with_assumption(actual_dt)

        # Combined: conservative confidence
        tz_confidence = min(promised_conf, actual_conf)
        tz_assumption = "SOURCE_TZ" if tz_confidence == 1.0 else "UTC_ASSUMED"

        # Deterministic ambiguity gate
        delta_minutes = abs((actual_utc - promised_utc).total_seconds()) / 60.0
        ambiguous_time = (tz_assumption != "SOURCE_TZ") and (delta_minutes < AMBIGUOUS_TIME_WINDOW_MINUTES)

        # 3) Service guarantee lookup (DB-driven)
        is_guaranteed = _is_service_guaranteed(db, carrier, service_norm)

        # 4) Exception resolution (Caveat #2 fix)
        exception_found, exception_category, exception_signal = _lookup_exception_rule(
            db=db,
            carrier=carrier,
            code=live_exception_code,
            text=live_exception_text
        )

        # 5) Deterministic eligibility
        is_late = actual_utc > promised_utc

        # Fail-closed if ambiguous timezone near threshold
        if ambiguous_time:
            is_eligible = False
            refundable_amount = Decimal("0.00")
            failure_reason = "Ambiguous delivery time (timezone)"
            rule_id = "RULE_TZ_AMBIGUOUS_FAIL_CLOSED"
        else:
            is_eligible = bool(is_late and is_guaranteed and not exception_found)
            refundable_amount = shipment.total_charged if is_eligible else Decimal("0.00")

            if exception_found:
                failure_reason = f"Excusable Delay ({exception_category})"
                rule_id = "RULE_EXCEPTION_RULES"
            elif not is_guaranteed:
                failure_reason = "Non-guaranteed service"
                rule_id = "RULE_SERVICE_NOT_GUARANTEED"
            elif is_late:
                failure_reason = "Late Delivery (GSR)"
                rule_id = "RULE_LATE_DELIVERY"
            else:
                failure_reason = None
                rule_id = "RULE_ON_TIME"

        # 6) Shipment upsert
        safe_json_data = shipment.model_dump(mode="json")
        ship_fields = {
            "service_type": service_norm if service_norm else shipment.service_type,
            "shipped_at": (shipment.shipped_at.astimezone(timezone.utc) if shipment.shipped_at.tzinfo else shipment.shipped_at.replace(tzinfo=timezone.utc)).isoformat(),
            "promised_delivery": promised_utc.isoformat(),
            "actual_delivery": actual_utc.isoformat(),
            "total_charged": float(shipment.total_charged),
            "weight_lbs": float(shipment.weight_value) if getattr(shipment, "weight_value", None) is not None else None,
            "raw_json_data": safe_json_data,
        }
        ship_row = _upsert_shipment(db, carrier, tracking, ship_fields)
        shipment_id = ship_row["id"]

        # 7) Audit upsert (now records caveat fields)
        audit_fields = {
            "is_eligible": is_eligible,
            "variance_amount": float(refundable_amount),
            "failure_reason": failure_reason,
            "rule_id": rule_id,
            "audited_at": datetime.now(timezone.utc).isoformat(),
            "timezone_assumption": tz_assumption,
            "timezone_confidence": float(tz_confidence),
            "exception_category": exception_category,
            "exception_signal": exception_signal
        }
        audit_row = _upsert_audit_result(db, shipment_id, audit_fields)
        audit_id = audit_row["id"]

        # 8) Claim upsert (only if eligible)
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
        raise HTTPException(status_code=500, detail=str(e))

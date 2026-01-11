from fastapi import APIRouter, HTTPException
from app.services.fedex import FedExService
from app.services.ups import UPSService
from app.services.audit import AuditEngine # <--- NEW IMPORT

router = APIRouter()
fedex_engine = FedExService()
ups_engine = UPSService()

@router.get("/track/fedex/{tracking_number}")
async def get_fedex(tracking_number: str):
    data = fedex_engine.track(tracking_number)
    if not data:
        raise HTTPException(status_code=404, detail="FedEx Asset Not Found")
    
    # Audit Trigger
    AuditEngine.log_event(data)
    return data

@router.get("/track/ups/{tracking_number}")
async def get_ups(tracking_number: str):
    data = ups_engine.track(tracking_number)
    if not data:
        raise HTTPException(status_code=404, detail="UPS Asset Not Found")
    
    # Audit Trigger
    AuditEngine.log_event(data)
    return data
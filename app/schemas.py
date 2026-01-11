# schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from decimal import Decimal

class ShipmentIngest(BaseModel):
    tracking_number: str = Field(..., description="Unique carrier tracking ID")
    carrier: str = Field(..., pattern="^(FedEx|UPS)$")
    service_type: str
    total_charged: Decimal = Field(..., gt=0)
    contract_rate: Decimal = Field(..., gt=0)
    shipped_at: datetime
    promised_delivery: datetime
    delivery_ts: datetime
    raw_metadata: Optional[dict[str, Any]] = {}

class AuditResponse(BaseModel):
    status: str
    tracking_number: str
    leakage_found: Decimal
    claim_status: str
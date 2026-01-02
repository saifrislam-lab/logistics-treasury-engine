from dotenv import load_dotenv
load_dotenv()

"""
Logistics Audit Engine - Production-Grade Backend
Ingests PDF invoices, extracts shipment data via OpenAI LLM, audits for refunds,
and generates recovery reports.
"""

import json
import os
import sys
from datetime import datetime
from typing import List, Optional
from pathlib import Path

import pandas as pd
import pdfplumber
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Pydantic Models for Data Validation
# ============================================================================

class Surcharge(BaseModel):
    """Individual surcharge item."""
    name: str
    amount: Optional[float] = None


class Shipment(BaseModel):
    """Shipment data structure with validation."""
    tracking_number: str = Field(..., description="Tracking number for the shipment")
    service_type: str = Field(..., description="Service type (e.g., Priority Overnight)")
    zone: Optional[str] = Field(None, description="Shipping zone")
    ship_date: str = Field(..., description="Ship date in YYYY-MM-DD format")
    delivery_date: str = Field(..., description="Delivery date in YYYY-MM-DD format")
    delivery_time: Optional[str] = Field(None, description="Delivery time in HH:MM format")
    promised_time: Optional[str] = Field(None, description="Promised delivery time in HH:MM format")
    weight: float = Field(..., description="Shipment weight in pounds")
    amount_charged: float = Field(..., description="Total amount charged for the shipment")
    surcharges: List[str] = Field(default_factory=list, description="List of surcharge names")
    status: Optional[str] = Field(None, description="Delivery status (e.g., 'Weather Delay')")

    @field_validator('amount_charged', 'weight')
    @classmethod
    def validate_non_negative(cls, v):
        if v < 0:
            raise ValueError('Value must be non-negative')
        return v


class AuditedShipment(BaseModel):
    """Shipment with audit results."""
    shipment: Shipment
    refund_eligible: bool = False
    refund_amount: float = 0.0
    audit_reason: str = ""
    potential_classification_error: bool = False
    classification_error_reason: str = ""


# ============================================================================
# OpenAI Client Initialization
# ============================================================================

def get_openai_client() -> OpenAI:
    """Initialize OpenAI client with API key from environment."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable not set. "
            "Please set it with: export OPENAI_API_KEY='your-key-here'"
        )
    return OpenAI(api_key=api_key)


# ============================================================================
# Data Ingestion
# ============================================================================

def ingest_invoice(pdf_path: str, client: OpenAI) -> List[Shipment]:
    """
    Extract shipment data from PDF invoice using OpenAI LLM.
    
    Args:
        pdf_path: Path to the PDF invoice file
        client: OpenAI client instance
        
    Returns:
        List of validated Shipment objects
    """
    try:
        # Extract raw text from PDF
        print(f"📄 Extracting text from PDF: {pdf_path}")
        text_content = ""
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"
        
        if not text_content.strip():
            raise ValueError("No text could be extracted from the PDF")
        
        print(f"✓ Extracted {len(text_content)} characters from PDF")
        
        # Prepare prompt for OpenAI
        prompt = """Extract all shipment details from this invoice text. Return a JSON object containing a list of shipments with these fields:

- tracking_number (string)
- service_type (string, e.g., "Priority Overnight", "Ground", "Express")
- zone (string, optional)
- ship_date (string, YYYY-MM-DD format)
- delivery_date (string, YYYY-MM-DD format)
- delivery_time (string, HH:MM format, optional)
- promised_time (string, HH:MM format, optional)
- weight (float, in pounds)
- amount_charged (float, in dollars)
- surcharges (list of strings, e.g., ["Residential", "Fuel Surcharge"])
- status (string, optional, e.g., "Weather Delay", "Delivered")

Return ONLY a valid JSON object with this structure:
{
  "shipments": [
    {
      "tracking_number": "...",
      "service_type": "...",
      ...
    }
  ]
}

Invoice text:
"""
        prompt += text_content[:15000]  # Limit to avoid token limits
        
        # Call OpenAI API
        print("🤖 Calling OpenAI API to extract shipment data...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a logistics data extraction expert. Extract shipment data from invoice text and return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        # Parse JSON response
        response_content = response.choices[0].message.content
        extracted_data = json.loads(response_content)
        
        # Validate and convert to Pydantic models
        shipments = []
        for item in extracted_data.get("shipments", []):
            try:
                shipment = Shipment(**item)
                shipments.append(shipment)
            except Exception as e:
                print(f"⚠️  Warning: Skipping invalid shipment data: {e}")
                continue
        
        print(f"✓ Successfully extracted {len(shipments)} shipments")
        return shipments
        
    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    except Exception as e:
        raise Exception(f"Error ingesting invoice: {str(e)}")


# ============================================================================
# Mock Data Generator
# ============================================================================

def generate_mock_invoice_text() -> str:
    """
    Generate mock invoice text for testing when no PDF is available.
    
    Returns:
        Mock invoice text string
    """
    mock_text = """
    FEDEX INVOICE
    Invoice Number: INV-2024-001234
    Date: 2024-01-15
    
    SHIPMENT DETAILS:
    
    Shipment 1:
    Tracking: 123456789012
    Service: Priority Overnight
    Zone: 2
    Ship Date: 2024-01-10
    Delivery Date: 2024-01-11
    Delivery Time: 14:30
    Promised Time: 10:30
    Weight: 25.5 lbs
    Amount: $125.50
    Surcharges: Fuel Surcharge, Residential
    Status: Delivered
    
    Shipment 2:
    Tracking: 987654321098
    Service: Ground
    Zone: 5
    Ship Date: 2024-01-08
    Delivery Date: 2024-01-12
    Delivery Time: 16:45
    Promised Time: 17:00
    Weight: 65.0 lbs
    Amount: $89.25
    Surcharges: Residential, Signature Required
    Status: Delivered
    
    Shipment 3:
    Tracking: 555555555555
    Service: Express Saver
    Zone: 3
    Ship Date: 2024-01-09
    Delivery Date: 2024-01-11
    Delivery Time: 11:00
    Promised Time: 12:00
    Weight: 15.0 lbs
    Amount: $42.75
    Surcharges: Fuel Surcharge
    Status: Delivered
    
    Shipment 4:
    Tracking: 777777777777
    Service: Standard Overnight
    Zone: 2
    Ship Date: 2024-01-11
    Delivery Date: 2024-01-12
    Delivery Time: 15:30
    Promised Time: 10:30
    Weight: 30.0 lbs
    Amount: $210.00
    Surcharges: Residential, Saturday Delivery
    Status: Weather Delay
    
    TOTAL AMOUNT: $467.50
    """
    return mock_text


def ingest_mock_data(client: OpenAI) -> List[Shipment]:
    """
    Generate and process mock invoice data for testing.
    
    Args:
        client: OpenAI client instance
        
    Returns:
        List of validated Shipment objects
    """
    print("📝 Using mock invoice data for testing...")
    mock_text = generate_mock_invoice_text()
    
    # Use OpenAI to extract from mock text
    prompt = """Extract all shipment details from this invoice text. Return a JSON object containing a list of shipments with these fields:

- tracking_number (string)
- service_type (string, e.g., "Priority Overnight", "Ground", "Express")
- zone (string, optional)
- ship_date (string, YYYY-MM-DD format)
- delivery_date (string, YYYY-MM-DD format)
- delivery_time (string, HH:MM format, optional)
- promised_time (string, HH:MM format, optional)
- weight (float, in pounds)
- amount_charged (float, in dollars)
- surcharges (list of strings, e.g., ["Residential", "Fuel Surcharge"])
- status (string, optional, e.g., "Weather Delay", "Delivered")

Return ONLY a valid JSON object with this structure:
{
  "shipments": [
    {
      "tracking_number": "...",
      "service_type": "...",
      ...
    }
  ]
}

Invoice text:
""" + mock_text
    
    try:
        print("🤖 Calling OpenAI API to extract shipment data from mock text...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a logistics data extraction expert. Extract shipment data from invoice text and return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        response_content = response.choices[0].message.content
        extracted_data = json.loads(response_content)
        
        shipments = []
        for item in extracted_data.get("shipments", []):
            try:
                shipment = Shipment(**item)
                shipments.append(shipment)
            except Exception as e:
                print(f"⚠️  Warning: Skipping invalid shipment data: {e}")
                continue
        
        print(f"✓ Successfully extracted {len(shipments)} shipments from mock data")
        return shipments
        
    except Exception as e:
        raise Exception(f"Error processing mock data: {str(e)}")


# ============================================================================
# Audit Logic
# ============================================================================

def parse_time(time_str: Optional[str]) -> Optional[datetime]:
    """Parse time string (HH:MM) into datetime.time object."""
    if not time_str:
        return None
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        return None


def run_audit(shipments: List[Shipment]) -> List[AuditedShipment]:
    """
    Run audit logic on shipments to identify refund opportunities.
    
    Logic A: Late Delivery - GSR (Guaranteed Service Refund)
    - If delivery_time > promised_time AND status is not "Weather Delay"
    - Mark refund_eligible = True, refund_amount = amount_charged
    
    Logic B: Residential Trap
    - If surcharges contains "Residential" AND weight > 50lbs
    - Flag as potential_classification_error
    
    Args:
        shipments: List of Shipment objects to audit
        
    Returns:
        List of AuditedShipment objects with audit results
    """
    print("\n🔍 Running audit logic...")
    audited_shipments = []
    
    for shipment in shipments:
        audited = AuditedShipment(shipment=shipment)
        
        # Logic A: Late Delivery - GSR
        if shipment.delivery_time and shipment.promised_time:
            delivery_time = parse_time(shipment.delivery_time)
            promised_time = parse_time(shipment.promised_time)
            
            if delivery_time and promised_time:
                # Check if delivery was late (and not weather delay)
                is_weather_delay = shipment.status and "Weather Delay" in shipment.status
                if delivery_time > promised_time and not is_weather_delay:
                    audited.refund_eligible = True
                    audited.refund_amount = shipment.amount_charged
                    audited.audit_reason = f"Late delivery: {shipment.delivery_time} vs promised {shipment.promised_time}"
        
        # Logic B: Residential Trap
        residential_surcharge = any(
            "residential" in surcharge.lower() 
            for surcharge in shipment.surcharges
        )
        if residential_surcharge and shipment.weight > 50.0:
            audited.potential_classification_error = True
            audited.classification_error_reason = (
                f"Residential surcharge applied to shipment >50lbs "
                f"(weight: {shipment.weight}lbs). May be misclassified."
            )
        
        audited_shipments.append(audited)
    
    # Count refund-eligible shipments
    refund_count = sum(1 for s in audited_shipments if s.refund_eligible)
    print(f"✓ Audit complete: {refund_count} shipments eligible for refund")
    
    return audited_shipments


# ============================================================================
# Report Generation
# ============================================================================

def generate_report(audited_shipments: List[AuditedShipment], output_path: str = "audit_report.csv") -> None:
    """
    Generate recovery report from audited shipments.
    
    Args:
        audited_shipments: List of AuditedShipment objects
        output_path: Path to save the CSV report
    """
    print(f"\n📊 Generating recovery report...")
    
    # Prepare data for DataFrame
    report_data = []
    for audited in audited_shipments:
        s = audited.shipment
        report_data.append({
            "Tracking Number": s.tracking_number,
            "Service Type": s.service_type,
            "Zone": s.zone,
            "Ship Date": s.ship_date,
            "Delivery Date": s.delivery_date,
            "Delivery Time": s.delivery_time,
            "Promised Time": s.promised_time,
            "Weight (lbs)": s.weight,
            "Amount Charged": s.amount_charged,
            "Surcharges": ", ".join(s.surcharges) if s.surcharges else "",
            "Status": s.status,
            "Refund Eligible": audited.refund_eligible,
            "Refund Amount": audited.refund_amount,
            "Audit Reason": audited.audit_reason,
            "Classification Error": audited.potential_classification_error,
            "Classification Error Reason": audited.classification_error_reason,
        })
    
    # Create DataFrame
    df = pd.DataFrame(report_data)
    
    # Calculate summary metrics
    total_spend = df["Amount Charged"].sum()
    total_recoverable = df["Refund Amount"].sum()
    roi_percentage = (total_recoverable / total_spend * 100) if total_spend > 0 else 0.0
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"✓ Report saved to: {output_path}")
    
    # Print Financial Summary
    print("\n" + "="*60)
    print("FINANCIAL SUMMARY")
    print("="*60)
    print(f"Total Shipments Analyzed: {len(audited_shipments)}")
    print(f"Total Spend: ${total_spend:,.2f}")
    print(f"Total Recoverable: ${total_recoverable:,.2f}")
    print(f"ROI Percentage: {roi_percentage:.2f}%")
    print(f"Refund-Eligible Shipments: {df['Refund Eligible'].sum()}")
    print(f"Potential Classification Errors: {df['Classification Error'].sum()}")
    print("="*60)
    
    if total_recoverable > 0:
        print(f"\n💰 DETECTED: ${total_recoverable:,.2f} in recoverable funds")
    else:
        print("\n✓ No recoverable funds detected in this audit")


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main execution function."""
    print("="*60)
    print("LOGISTICS AUDIT ENGINE")
    print("="*60)
    print()
    
    try:
        # Initialize OpenAI client
        client = get_openai_client()
        
        # Determine input source (PDF or mock data)
        if len(sys.argv) > 1:
            pdf_path = sys.argv[1]
            if not Path(pdf_path).exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            shipments = ingest_invoice(pdf_path, client)
        else:
            print("⚠️  No PDF file provided. Using mock data for testing.")
            print("   Usage: python main.py <path_to_invoice.pdf>")
            print()
            shipments = ingest_mock_data(client)
        
        if not shipments:
            print("⚠️  No shipments found in invoice.")
            return
        
        # Run audit
        audited_shipments = run_audit(shipments)
        
        # Generate report
        generate_report(audited_shipments)
        
        print("\n✅ Audit complete!")
        
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n❌ File Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


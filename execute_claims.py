import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# --- CONFIGURATION ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Critical Error: API Keys missing.")
    exit()

# Institutional Client Connection
db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def execute_batch():
    print(f"🚀 [EXECUTION] Starting Claims Processing Protocol...")
    
    # 1. QUERY THE VAULT
    # We fetch Audit Results linked to Claims that are still in 'DRAFT'
    # This ensures we don't re-export old claims.
    response = db.table("claims").select(
        "id, claim_amount, status, shipment_id, audit_id"
    ).eq("status", "DRAFT").execute()
    
    claims_data = response.data
    
    if not claims_data:
        print("✅ No pending claims found. The Ledger is clear.")
        return

    print(f"📊 [INVENTORY] Found {len(claims_data)} actionable claims.")
    
    # 2. ENRICH DATA (Join with Shipment Details)
    export_rows = []
    ids_to_update = []
    
    total_liquidity = 0.0

    for claim in claims_data:
        # Fetch underlying asset details
        # Note: In a larger system, we'd do a joined query. Here we loop for precision control.
        ship_res = db.table("shipments").select("*").eq("id", claim['shipment_id']).execute()
        audit_res = db.table("audit_results").select("*").eq("id", claim['audit_id']).execute()
        
        if ship_res.data and audit_res.data:
            shipment = ship_res.data[0]
            audit = audit_res.data[0]
            
            # --- BUILD THE ARTIFACT ---
            # This format is tuned for a standard "Service Failure" bulk dispute
            row = {
                "Tracking Number": shipment['tracking_number'],
                "Carrier": shipment['carrier'],
                "Dispute Type": "Service Failure (GSR)",
                "Claim Amount": f"${claim['claim_amount']:.2f}",
                "Currency": "USD",
                "Invoice Date": datetime.now().strftime("%Y-%m-%d"), # Today's filing date
                "Reason Code": "LATE_DELIVERY",
                "Notes": f"Audit: Promised {shipment['promised_delivery']} vs Actual {shipment['actual_delivery']}"
            }
            
            export_rows.append(row)
            ids_to_update.append(claim['id'])
            total_liquidity += float(claim['claim_amount'])

    # 3. GENERATE THE ASSET (CSV)
    if export_rows:
        df = pd.DataFrame(export_rows)
        filename = f"UPS_CLAIM_BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        df.to_csv(filename, index=False)
        print(f"\n💰 [ASSET GENERATED] {filename}")
        print(f"   Total Value: ${total_liquidity:,.2f}")
        
        # 4. CLOSE THE LOOP (State Management)
        # Update Ledger status from 'DRAFT' to 'SUBMITTED'
        print("🔒 [LEDGER] Locking claims as SUBMITTED...")
        for cid in ids_to_update:
            db.table("claims").update({
                "status": "SUBMITTED",
                "submitted_at": datetime.now().isoformat()
            }).eq("id", cid).execute()
            
        print("✅ Batch Execution Complete.")
    
    else:
        print("⚠️ Error: Could not correlate shipment data.")

if __name__ == "__main__":
    execute_batch()
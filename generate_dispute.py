import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# --- CONFIGURATION ---
SUPABASE_URL = "https://zclwtzzzdzrjoxqkklyt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpjbHd0enp6ZHpyam94cWtrbHl0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzY2NzMxMCwiZXhwIjoyMDgzMjQzMzEwfQ.VtFzPmoOGIo3sl8AQ6w69odkgmQ03mqlbwYoecvuEKg"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_fedex_dispute_artifact():
    print("⚖️ [LEGAL] Generating Dispute Artifacts...")

    # 1. Fetch actionable refunds (PENDING or POTENTIAL_REFUND)
    # We filter for rows that haven't been submitted yet
    response = supabase.table("shipments").select("*").eq("audit_status", "POTENTIAL_REFUND").execute()
    shipments = response.data

    if not shipments:
        print("✅ No new claims to generate.")
        return

    # 2. Format for FedEx Billing Online (Standard CSV Layout)
    # Columns: Tracking ID, Invoice Date, Invoice Number, Dispute Type, Dispute Amount, Comments
    dispute_rows = []
    
    for item in shipments:
        dispute_rows.append({
            "Tracking ID": item['tracking_number'],
            "Dispute Type": "5",  # FedEx Code for 'Service Failure'
            "Dispute Amount": item['predicted_refund'],
            "Comments": "Guaranteed Service Refund - Late Delivery"
        })

    if dispute_rows:
        # 3. Create the Artifact
        df = pd.DataFrame(dispute_rows)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"fedex_dispute_artifact_{timestamp}.csv"
        
        df.to_csv(filename, index=False)
        print(f"📄 [ARTIFACT] Generated claim file: {filename}")
        print(f"💰 [VALUE] Total Value: ${df['Dispute Amount'].sum():.2f}")

        # 4. Update Database State (Lock the rows)
        # We mark them as 'SUBMITTED' so we know the ball is in FedEx's court.
        ids_to_update = [x['id'] for x in shipments]
        for uid in ids_to_update:
            supabase.table("shipments").update({
                "audit_status": "SUBMITTED"
            }).eq("id", uid).execute()
            
        print("🔒 [VAULT] Shipments marked as SUBMITTED. Waiting for Carrier Credit.")

if __name__ == "__main__":
    generate_fedex_dispute_artifact()
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# 1. Fetch all eligible audit results that don't have a claim yet
eligible = supabase.table("audit_results").select("*").eq("is_eligible", True).execute()

for item in eligible.data:
    # 2. Insert into the claims table as 'DRAFT'
    supabase.table("claims").insert({
        "shipment_id": item['shipment_id'],
        "claim_amount": item['variance_amount'],
        "status": "DRAFT",
        "reason": item['failure_reason']
    }).execute()

print(f"✅ Promoted {len(eligible.data)} assets to the Claims Queue.")
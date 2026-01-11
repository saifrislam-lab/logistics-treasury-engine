import pandas as pd
from supabase import create_client, Client

# --- CONFIGURATION ---
SUPABASE_URL = "https://zclwtzzzdzrjoxqkklyt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpjbHd0enp6ZHpyam94cWtrbHl0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzY2NzMxMCwiZXhwIjoyMDgzMjQzMzEwfQ.VtFzPmoOGIo3sl8AQ6w69odkgmQ03mqlbwYoecvuEKg"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# The standard industry divisor
FEDEX_DIM_DIVISOR = 139 

def run_rate_audit():
    print("📏 [OPTIMIZER] Scanning for Dimensional Weight Alpha...")
    
    # Pull shipments that haven't been rate-audited
    response = supabase.table("shipments").select("*").execute()
    shipments = response.data

    for item in shipments:
        # Check if we have dimensions (e.g., "18x18x18")
        dims_raw = item.get("dims")
        if dims_raw and "x" in dims_raw:
            try:
                l, w, h = map(float, dims_raw.lower().split('x'))
                dim_weight = (l * w * h) / FEDEX_DIM_DIVISOR
                billed_weight = float(str(item['weight_billed']).split()[0])

                if dim_weight > billed_weight:
                    # This package is 'Light but Large' - prime for optimization
                    potential_saving = item['net_charge'] * 0.15 # Typical 15% saving via box reduction
                    
                    print(f"📦 [OPTIMIZE] Tracking {item['tracking_number']}: Charged {billed_weight}lbs but Dim-Weight is {dim_weight:.1f}lbs")
                    
                    supabase.table("shipments").update({
                        "audit_status": "DIM_WEIGHT_ERROR",
                        "predicted_refund": item['predicted_refund'] + potential_saving
                    }).eq("id", item['id']).execute()
            except:
                continue

    print("🏁 [COMPLETE] Rate Optimization Audit finished.")

if __name__ == "__main__":
    run_rate_audit()
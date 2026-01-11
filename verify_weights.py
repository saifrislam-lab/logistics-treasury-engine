# verify_weights.py
# ---------------------------------------------------------
# INSTITUTIONAL GRADE VERIFICATION SCRIPT
# PURPOSE: Validate Dimensional Weight Logic (Model 3.0)
# ---------------------------------------------------------

import sys
# Simulating the logic from your rate_optimizer.py
# (We import it directly if available, or mock it here for verification)

def calculate_dim_weight(length, width, height, divisor=139):
    """
    Standard Institutional Formula: (L x W x H) / Divisor
    FedEx/UPS Standard Divisor is usually 139 for daily rates.
    """
    volumetric = (length * width * height) / divisor
    return round(volumetric, 2)

def audit_shipment(tracking_id, actual_weight, l, w, h, billed_weight):
    print(f"\n--- AUDITING ASSET: {tracking_id} ---")
    
    # 1. Calculate Theoretical Dim Weight
    dim_weight = calculate_dim_weight(l, w, h)
    print(f"📦 Physical Dims: {l}x{w}x{h}")
    print(f"⚖️ Actual Scale Weight: {actual_weight} lbs")
    print(f"📐 Calculated Dim Weight: {dim_weight} lbs")
    
    # 2. Compare against Carrier Billed Weight
    print(f"🧾 Carrier Billed Weight: {billed_weight} lbs")
    
    # 3. Detect Leakage (Arbitrage Opportunity)
    if billed_weight > max(actual_weight, dim_weight):
        variance = billed_weight - max(actual_weight, dim_weight)
        print(f"🚨 ALERT: Overcharge Detected! Carrier billed {variance:.2f} lbs over logic.")
        return "CLAIM_ELIGIBLE"
    elif dim_weight > actual_weight and billed_weight == int(dim_weight + 0.99):
         print(f"✅ Efficient Billing: Carrier correctly billed by volume.")
         return "CLEAN"
    else:
        print(f"⚠️ ANOMALY: Billing logic unclear. Requires manual review.")
        return "REVIEW"

# --- RUN SIMULATION ---
if __name__ == "__main__":
    print("running verify_weights.py...")
    
    # Scenario 1: The "Air" Shipment (Paying for volume)
    # Box is light (5 lbs) but big (12x12x12). Should bill at ~13 lbs.
    audit_shipment("TRK_001", actual_weight=5, l=12, w=12, h=12, billed_weight=13)

    # Scenario 2: The "Heavy" Shipment (Paying for density)
    # Box is small (5x5x5) but heavy (20 lbs). Should bill at 20 lbs.
    audit_shipment("TRK_002", actual_weight=20, l=5, w=5, h=5, billed_weight=20)
    
    # Scenario 3: The "Leakage" (Carrier Error)
    # Box is 10x10x10 (Dim ~7.2 lbs). Actual 5 lbs. Carrier billed 15 lbs.
    audit_shipment("TRK_003", actual_weight=5, l=10, w=10, h=10, billed_weight=15)
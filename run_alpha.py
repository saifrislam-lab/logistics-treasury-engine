import subprocess
import time
import sys

def execute_pipeline():
    print("🚀 [INITIATING] Carrier Alpha Treasury Sequence...")
    
    # 1. RUN INGESTION
    print("\n📦 STEP 1: Ingesting Invoice...")
    subprocess.run([sys.executable, "ingest_engine_v2.py"])
    
    # 2. RUN AUDIT
    print("\n🔍 STEP 2: Scanning for Alpha...")
    subprocess.run([sys.executable, "audit_logic.py"])
    
    # 3. LAUNCH DASHBOARD
    print("\n📊 STEP 3: Launching Treasury Terminal...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "carrier_alpha.py"])

if __name__ == "__main__":
    execute_pipeline()
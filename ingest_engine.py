import pdfplumber
import pandas as pd
import re

# ==================================================
# 🧠 CARRIER ALPHA: INGESTION ENGINE (v1.4 - TABLE MINER)
# ==================================================

class CarrierIngestor:
    def __init__(self):
        # We keep regex only for cleaning specific cells now
        self.patterns = {
            'tracking_clean': r'[^a-zA-Z0-9]', # Remove spaces/dashes
            'price_clean': r'[^\d.]'            # Remove '$' and ','
        }

    def parse_pdf(self, pdf_path):
        print(f"🔄 [INGEST] Mining tables from artifact: {pdf_path}...")
        extracted_rows = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # STRATEGY 2: TABLE EXTRACTION
                    # We ask pdfplumber to find the visual grid (lines)
                    tables = page.extract_tables()
                    
                    for table in tables:
                        for row in table:
                            # We filter out empty rows or headers
                            clean_row = [str(cell).replace('\n', ' ') if cell else '' for cell in row]
                            
                            # LOGIC: A valid shipment row usually has a Tracking # and a Price
                            # We check if any cell looks like a tracking number (12+ digits)
                            if self._is_valid_shipment_row(clean_row):
                                structured_data = self._map_row_to_schema(clean_row)
                                extracted_rows.append(structured_data)
                        
            count = len(extracted_rows)
            if count == 0:
                print("⚠️ [DIAGNOSTIC] Table Strategy yielded 0 records.")
                print("   (The PDF might not have grid lines, or column mapping is off.)")
            else:
                print(f"✅ [SUCCESS] Mined {count} shipment records from tables.")
                
            return pd.DataFrame(extracted_rows)
            
        except Exception as e:
            print(f"⚠️ [ERROR] Ingestion failed: {e}")
            return pd.DataFrame()

    def _is_valid_shipment_row(self, row):
        """
        Scans a row to see if it contains a potential tracking number.
        This filters out headers like 'Date', 'Description', 'Amount'.
        """
        # Join row to string to search for a tracking-like pattern
        row_str = " ".join(row)
        # Look for 12+ digits or 1Z...
        is_tracking = re.search(r'(\b1Z[A-Z0-9]{16}\b|\b\d{12,15}\b)', row_str.replace(" ", ""))
        return bool(is_tracking)

    def _map_row_to_schema(self, row):
        """
        INTELLIGENT MAPPING:
        Since we don't know which column is which, we guess based on content.
        """
        record = {
            "tracking_id": "N/A",
            "service_type": "N/A",
            "weight": "N/A",
            "dims": "N/A",
            "net_charge": "0.00"
        }
        
        for cell in row:
            # CLEAN UP
            clean_cell = cell.strip()
            
            # 1. IDENTIFY TRACKING (Long alphanumeric)
            clean_track = re.sub(r'\s+', '', clean_cell) # remove spaces
            if re.match(r'^(1Z[A-Z0-9]{16}|\d{12,15})$', clean_track):
                record['tracking_id'] = clean_track
                continue
                
            # 2. IDENTIFY PRICE ($ sign or decimal format)
            if '$' in clean_cell or re.match(r'^\d+\.\d{2}$', clean_cell):
                # We assume the last price found is the Net Charge (often correct)
                record['net_charge'] = clean_cell
                continue
            
            # 3. IDENTIFY WEIGHT (Contains LBS/KGS)
            if re.search(r'(LBS|KG|lbs|kg)', clean_cell):
                record['weight'] = clean_cell
                continue

            # 4. IDENTIFY DIMS (Contains 'x')
            if re.search(r'\d+\s*x\s*\d+\s*x\s*\d+', clean_cell):
                record['dims'] = clean_cell
                continue
                
            # 5. IDENTIFY SERVICE (Keywords)
            if re.search(r'(Priority|Ground|Standard|Express|Next Day)', clean_cell, re.IGNORECASE):
                record['service_type'] = clean_cell

        return record

# ==========================================
# 🚀 MAIN EXECUTION BLOCK
# ==========================================
if __name__ == "__main__":
    engine = CarrierIngestor()
    # Ensure this filename matches exactly what is in your folder!
    target_file = "fedex_invoice_sample.pdf" 
    
    df = engine.parse_pdf(target_file)
    
    print("\n📊 CARRIER ALPHA | TABLE MINER RESULTS")
    print("=========================================================================")
    if not df.empty:
        # Reorder columns for readability if they exist
        cols = [c for c in ['tracking_id', 'service_type', 'weight', 'dims', 'net_charge'] if c in df.columns]
        print(df[cols].to_string(index=False))
        print("\n-------------------------------------------------------------------------")
        print(f"📦 SHIPMENTS MINED: {len(df)}")
    else:
        print("❌ No data found. (Next Step: OCR Strategy)")
    print("=========================================================================")
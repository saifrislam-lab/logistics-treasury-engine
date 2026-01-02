from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import random
from datetime import datetime, timedelta

def create_mock_invoice(filename="fedex_invoice_mock.pdf"):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    # --- HEADER ---
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(colors.purple)
    c.drawString(50, 750, "FedEx")
    c.setFillColor(colors.orange)
    c.drawString(130, 750, "Express")
    
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(400, 760, f"Invoice Number: 7-994-221")
    c.drawString(400, 745, f"Invoice Date: {datetime.now().strftime('%Y-%m-%d')}")
    c.drawString(400, 730, "Account Number: 1234-5678-9")
    
    c.line(50, 720, 560, 720)

    # --- SUMMARY SECTION ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 690, "Consolidated Invoice Summary")
    c.setFont("Helvetica", 10)
    c.drawString(50, 670, "Original Amount Due:")
    c.drawString(500, 670, "$467.50")
    c.drawString(50, 655, "Current Balance:")
    c.drawString(500, 655, "$467.50")

    # --- SHIPMENT DETAILS HEADERS ---
    y = 600
    c.setFillColor(colors.lightgrey)
    c.rect(40, y, 520, 20, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    headers = ["Tracking ID", "Service", "Weight", "Ship Date", "Delivery", "Charge"]
    x_positions = [50, 150, 250, 310, 390, 500]
    
    for i, h in enumerate(headers):
        c.drawString(x_positions[i], y+6, h)

    # --- MOCK SHIPMENTS ---
    shipments = [
        # 1. THE LATE DELIVERY ($125.50 Refund)
        { "id": "1Z9928392", "svc": "Priority Overnight", "wgt": "12 lbs", "ship": (datetime.now() - timedelta(days=5)).strftime('%m/%d'), "del": "14:15 (LATE)", "cost": "$125.50" },
        # 2. THE RESIDENTIAL TRAP ($5.50 Refund)
        { "id": "1Z5543221", "svc": "Ground Commercial", "wgt": "55 lbs", "ship": (datetime.now() - timedelta(days=4)).strftime('%m/%d'), "del": "10:00", "cost": "$42.10", "extra": "Residential Surcharge" },
        # 3. CLEAN SHIPMENT
        { "id": "1Z4432119", "svc": "Standard Overnight", "wgt": "2 lbs", "ship": (datetime.now() - timedelta(days=3)).strftime('%m/%d'), "del": "14:30", "cost": "$28.00" },
        # 4. CLEAN SHIPMENT
        { "id": "1Z3321994", "svc": "Ground", "wgt": "5 lbs", "ship": (datetime.now() - timedelta(days=2)).strftime('%m/%d'), "del": "11:45", "cost": "$14.50" }
    ]

    y = 570
    c.setFont("Helvetica", 9)
    for s in shipments:
        c.drawString(x_positions[0], y, s["id"])
        c.drawString(x_positions[1], y, s["svc"])
        c.drawString(x_positions[2], y, s["wgt"])
        c.drawString(x_positions[3], y, s["ship"])
        c.drawString(x_positions[4], y, s["del"])
        c.drawString(x_positions[5], y, s["cost"])
        if "extra" in s:
            y -= 12
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(x_positions[1], y, f"Includes: {s['extra']}")
            c.setFont("Helvetica", 9)
        y -= 25

    c.save()
    print(f"✅ Generated institutional test asset: {filename}")

if __name__ == "__main__":
    create_mock_invoice()
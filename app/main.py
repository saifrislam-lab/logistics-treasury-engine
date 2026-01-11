from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.tracking import router as tracking_router
from app.routers.ingest import router as ingest_router # <--- NEW IMPORT

app = FastAPI(title="Logistics Treasury Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tracking_router)
app.include_router(ingest_router) # <--- NEW REGISTRATION

@app.get("/")
async def root():
    return {"status": "ONLINE", "engine": "Treasury V1"}
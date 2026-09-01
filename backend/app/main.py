from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.vehicles import router as vehicles_router
from app.api.analytics import router as analytics_router
from app.api.alerts import router as alerts_router
from app.api.blacklist import router as blacklist_router
from app.api.perception import router as perception_router
from app.api.ws import router as ws_router

app = FastAPI(
    title="TRACE API",
    version="0.1.0",
    description="Tracking, Recognition, Analytics & City-wide Traffic Enforcement"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "TRACE API"}

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(vehicles_router, prefix="", tags=["Vehicles"])
app.include_router(analytics_router, prefix="", tags=["Analytics"])
app.include_router(alerts_router, prefix="", tags=["Alerts"])
app.include_router(blacklist_router, prefix="", tags=["Blacklist"])
app.include_router(perception_router, prefix="", tags=["Perception"])
app.include_router(ws_router, prefix="", tags=["WebSocket"])

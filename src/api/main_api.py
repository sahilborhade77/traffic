"""
Feature 6: FastAPI REST Dashboard Backend
-----------------------------------------
Real-time admin API with endpoints for:
- Live violation feed
- Plate search
- Fine payment status update
- Camera health status
CPU-only service. VRAM cost: 0.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import logging
import uvicorn
import sys
import os

sys.path.append(os.getcwd())
from src.database.violation_db import ViolationDatabase, Violation

logger = logging.getLogger(__name__)

# ── App Init ──
app = FastAPI(
    title="Traffic Intelligence System — Admin API",
    description="Real-time monitoring and enforcement management for TIS.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ── Global DB (initialized on startup) ──
db: Optional[ViolationDatabase] = None

@app.on_event("startup")
async def startup():
    global db
    db_url = os.getenv('DATABASE_URL', 'sqlite:///traffic.db')
    db = ViolationDatabase(db_url=db_url)
    logger.info("TIS API started. DB connected.")

# ── Pydantic Models ──
class ViolationOut(BaseModel):
    violation_id: int
    plate_number: Optional[str]
    violation_type: str
    camera_id: str
    location: str
    timestamp: datetime
    fine_amount: Optional[float]
    fine_status: str
    image_path: Optional[str]

    class Config:
        from_attributes = True

class PaymentUpdate(BaseModel):
    fine_status: str  # paid, disputed, cancelled

class CameraStatus(BaseModel):
    camera_id: str
    is_active: bool
    last_seen: Optional[datetime]

# ── Endpoints ──

@app.get("/", tags=["Health"])
def root():
    return {"status": "online", "system": "Traffic Intelligence System v2.0"}

@app.get("/violations/recent", response_model=List[ViolationOut], tags=["Violations"])
def get_recent_violations(limit: int = Query(50, le=200)):
    """Fetch the most recent N violations for the live feed."""
    violations = db.session.query(Violation)\
        .order_by(Violation.timestamp.desc())\
        .limit(limit).all()
    return violations

@app.get("/violations/plate/{plate_number}", tags=["Violations"])
def get_violations_by_plate(plate_number: str, days: int = 30):
    """Search all violations for a given license plate."""
    violations = db.get_violations_by_plate(plate_number, days=days)
    if not violations:
        raise HTTPException(status_code=404, detail=f"No violations found for plate {plate_number}")
    return violations

@app.patch("/violations/{violation_id}/payment", tags=["Violations"])
def update_payment_status(violation_id: int, update: PaymentUpdate):
    """Update fine payment status (paid, disputed, cancelled)."""
    allowed_statuses = {'pending', 'paid', 'disputed', 'cancelled'}
    if update.fine_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of {allowed_statuses}")
    
    violation = db.session.query(Violation).get(violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    
    violation.fine_status = update.fine_status
    violation.updated_at = datetime.now()
    db.session.commit()
    return {"violation_id": violation_id, "new_status": update.fine_status, "message": "Updated successfully"}

@app.get("/stats/summary", tags=["Analytics"])
def get_summary_stats():
    """Live summary statistics for the dashboard."""
    total = db.session.query(Violation).count()
    pending = db.session.query(Violation).filter(Violation.fine_status == 'pending').count()
    paid = db.session.query(Violation).filter(Violation.fine_status == 'paid').count()
    
    # Violations by type
    from sqlalchemy import func
    by_type = db.session.query(
        Violation.violation_type,
        func.count(Violation.violation_id)
    ).group_by(Violation.violation_type).all()
    
    return {
        "total_violations": total,
        "pending_payment": pending,
        "paid": paid,
        "violations_by_type": {vtype: count for vtype, count in by_type}
    }

@app.get("/cameras/status", tags=["Infrastructure"])
def get_camera_status():
    """Returns health status of all configured cameras."""
    # Returns placeholder — in production, integrate with your RTSP health checker
    cameras = [
        {"camera_id": "CAM_001", "name": "North Entry",    "is_active": True,  "type": "entry"},
        {"camera_id": "CAM_002", "name": "North Exit",     "is_active": True,  "type": "exit"},
        {"camera_id": "CAM_003", "name": "South Junction", "is_active": False,  "type": "junction"},
    ]
    return cameras

if __name__ == "__main__":
    uvicorn.run("src.api.main_api:app", host="0.0.0.0", port=8000, reload=True)

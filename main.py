# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 

import logging
import os
from pathlib import Path
from threading import Event, Thread
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import ColumnElement, cast, String, text
from typing import cast as py_cast

from core.database import engine, get_db, Base, SessionLocal
from core.security import get_current_user
from services.container_service import ContainerService
from services.transnet_service import run_transnet_ingest

# Import all models to register them
from models.user import User
from models.booking import Booking
from models.downtime import Downtime
from models.cargo import CargoItem
from models.container import Container, ContainerStatus
from models.evidence import ContainerImage
from models.packing import PackingSession
from models.unpacking import UnpackingSession
from models.plan import Plan
from models.truck_offloading import TruckOffloading
from models.backload_truck import BackloadTruck, BackloadCargoItem
from models.damage_report import DamageReport, DamageReportPhoto
from models.operational_incident import OperationalIncident, OperationalIncidentPhoto
from models.transnet import TransnetVesselStack

# Import routers
from api import auth, containers, planning, bookings, packing_workflow, unpacking_workflow, truck_offloading, backload_truck, packing, unpacking, admin, damage_reports, transnet, operational_incidents

def ensure_damage_report_schema() -> None:
    if not engine.url.drivername.startswith("sqlite"):
        return

    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='damage_reports'")
        ).fetchone()
        if not exists:
            return

        cols = conn.execute(text("PRAGMA table_info(damage_reports)")).fetchall()
        col_names = {row[1] for row in cols}

        if "is_resolved" not in col_names:
            conn.execute(text("ALTER TABLE damage_reports ADD COLUMN is_resolved BOOLEAN NOT NULL DEFAULT 0"))
        if "resolved_notes" not in col_names:
            conn.execute(text("ALTER TABLE damage_reports ADD COLUMN resolved_notes TEXT"))
        if "resolved_at" not in col_names:
            conn.execute(text("ALTER TABLE damage_reports ADD COLUMN resolved_at DATETIME"))
        if "resolved_by" not in col_names:
            conn.execute(text("ALTER TABLE damage_reports ADD COLUMN resolved_by TEXT"))


# Create database tables
Base.metadata.create_all(bind=engine)
ensure_damage_report_schema()

# Initialize FastAPI app
app = FastAPI(
    title="PortGuard CCMS v3",
    description="Port of Durban Container Clearing & Monitoring System",
    version="3.0.0"
)

log = logging.getLogger(__name__)

# Mount file storage
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Mount static assets (CSS, JS)
STATIC_DIR = Path("static")
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Register routers
app.include_router(auth.router)
app.include_router(containers.router, prefix="/api")
app.include_router(planning.router, prefix="/api")
app.include_router(packing_workflow.router, prefix="/api")
app.include_router(unpacking_workflow.router)
app.include_router(bookings.router, prefix="/api")
app.include_router(truck_offloading.router)
app.include_router(backload_truck.router)
app.include_router(packing.router, prefix="/api")
app.include_router(unpacking.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(damage_reports.router, prefix="/api")
app.include_router(transnet.router)
app.include_router(operational_incidents.router, prefix="/api")


def _transnet_scheduler_loop(stop_event: Event) -> None:
    interval_minutes = int(os.getenv("TRANSNET_SCRAPE_INTERVAL_MINUTES", "60"))
    source_url = os.getenv(
        "TRANSNET_SCRAPE_URL",
        "https://www.transnetportterminals.net/Ports/Pages/Terminal%20Updates.aspx",
    )

    while not stop_event.is_set():
        db = None
        try:
            db = SessionLocal()
            run_transnet_ingest(db, source_url, run_type="scheduled")
        except Exception as exc:
            log.error("Scheduled Transnet scrape failed: %s", exc, exc_info=True)
        finally:
            if db:
                db.close()

        stop_event.wait(interval_minutes * 60)


@app.on_event("startup")
def start_background_jobs() -> None:
    enabled = os.getenv("TRANSNET_SCRAPE_ENABLED", "false").lower() in {"1", "true", "yes"}
    if not enabled:
        log.info("Transnet scheduler disabled. Set TRANSNET_SCRAPE_ENABLED=true to enable.")
        return

    stop_event = Event()
    thread = Thread(target=_transnet_scheduler_loop, args=(stop_event,), daemon=True)
    thread.start()
    app.state.transnet_stop_event = stop_event
    app.state.transnet_thread = thread


@app.on_event("shutdown")
def stop_background_jobs() -> None:
    stop_event = getattr(app.state, "transnet_stop_event", None)
    if stop_event:
        stop_event.set()


# ==================== HEALTH CHECK ====================
@app.get("/health")
def health_check():
    """Health check endpoint for Docker and Kubernetes."""
    return {
        "status": "healthy",
        "service": "PortGuard CCMS v3",
        "version": "3.0.0"
    }


@app.get("/")
def home(request: Request):
    """Display the home page."""
    return templates.TemplateResponse("index.html", {"request": request})



# ==================== LOGIN PAGE ====================
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Display the login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    """Display the registration page."""
    return templates.TemplateResponse("register.html", {"request": request})


# ==================== DASHBOARD ====================
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    current_user = Depends(get_current_user)
):
    """Display the dashboard (requires authentication)."""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_email": current_user.email,
        "user_role": current_user.role
    })


@app.get("/operator-dashboard", response_class=HTMLResponse)
def operator_dashboard(
    request: Request,
    current_user = Depends(get_current_user)
):
    """Display the operational dashboard for tally clerks and team leaders."""
    # Check if user has operator-level access
    if current_user.role not in ["OPERATOR", "SUPERVISOR", "ADMIN", "SUPERUSER"]:
        raise HTTPException(status_code=403, detail="Access Denied")
    
    return templates.TemplateResponse("operator_dashboard.html", {
        "request": request,
        "user_email": current_user.email,
        "user_role": current_user.role,
        "user_name": current_user.username
    })


@app.get("/supervisor-dashboard", response_class=HTMLResponse)
def supervisor_dashboard(
    request: Request,
    current_user = Depends(get_current_user)
):
    """Display the supervisor audit dashboard (requires supervisor access)."""
    if current_user.role not in ["SUPERVISOR", "ADMIN", "SUPERUSER"]:
        raise HTTPException(status_code=403, detail="Access Denied")

    return templates.TemplateResponse("supervisor_dashboard.html", {
        "request": request,
        "user_email": current_user.email,
        "user_role": current_user.role,
        "user_name": current_user.username
    })


@app.get("/admin-dashboard", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    current_user = Depends(get_current_user)
):
    """Display the admin dashboard (requires admin access)."""
    if current_user.role not in ["ADMIN", "SUPERUSER"]:
        raise HTTPException(status_code=403, detail="Access Denied")

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "user_email": current_user.email,
        "user_role": current_user.role,
        "user_name": current_user.username
    })


@app.get("/manager-dashboard", response_class=HTMLResponse)
def manager_dashboard(
    request: Request,
    current_user = Depends(get_current_user)
):
    """Display the manager dashboard (requires manager access)."""
    if current_user.role not in ["MANAGER", "ADMIN", "SUPERUSER"]:
        raise HTTPException(status_code=403, detail="Access Denied")

    return templates.TemplateResponse("manager_dashboard.html", {
        "request": request,
        "user_email": current_user.email,
        "user_role": current_user.role,
        "user_name": current_user.username
    })


# ==================== API: HEALTH CHECK ====================
@app.get("/api/health")
def api_health():
    """API health check endpoint."""
    return {
        "status": "operational",
        "version": "3.0.0",
        "service": "PortGuard CCMS"
    }


# ==================== API: DASHBOARD STATS ====================
@app.get("/api/dashboard-stats")
def api_dashboard_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get dashboard statistics for the operational dashboard."""
    try:
        total = db.query(Container).count()
        pending = db.query(Container).filter(
            Container.status == ContainerStatus.PENDING_REVIEW  # type: ignore
        ).count()
        repairs = db.query(Container).filter(
            Container.needs_repair.is_(True)
        ).count()
        
        return {
            "total": total,
            "pending": pending,
            "repairs": repairs,
            "status": "success"
        }
    except Exception as e:
        return {
            "total": 0,
            "pending": 0,
            "repairs": 0,
            "error": str(e)
        }


# ==================== QR VERIFICATION ====================
@app.get("/verify/{container_id}", response_class=HTMLResponse)
def verify_container_qr(
    request: Request,
    container_id: str,
    db: Session = Depends(get_db)
):
    """QR code verification endpoint for gate scanning."""
    try:
        container = ContainerService.get_container(container_id, db)
        container_status = container.status.value if hasattr(container.status, 'value') else str(container.status)
        is_finalized = container_status == ContainerStatus.FINALIZED.value
        
        return templates.TemplateResponse("verify.html", {
            "request": request,
            "container_no": container.container_no,
            "container_id": container_id,
            "status_text": "VERIFIED" if is_finalized else "PENDING",
            "status_class": "verified" if is_finalized else "pending",
            "message": "Official PortGuard Digital Match" if is_finalized else "Awaiting Finalization"
        })
    except Exception as e:
        return templates.TemplateResponse("verify.html", {
            "request": request,
            "container_no": "UNKNOWN",
            "container_id": container_id,
            "status_text": "ERROR",
            "status_class": "error",
            "message": str(e)
        })


# ==================== TAB TEMPLATES ====================
@app.get("/templates/tabs/{tab_name}.html", response_class=HTMLResponse)
def get_tab_template(tab_name: str):
    """Serve individual tab templates for dynamic loading."""
    tab_file = Path(f"templates/tabs/{tab_name}.html")
    if not tab_file.exists():
        return f"<!-- Tab template {tab_name}.html not found --><p>Error: Tab not found</p>"
    
    try:
        return tab_file.read_text(encoding='utf-8')
    except Exception as e:
        return f"<!-- Error loading tab: {str(e)} --><p>Error: {str(e)}</p>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

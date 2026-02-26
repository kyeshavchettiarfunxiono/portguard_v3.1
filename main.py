# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 

import logging
import os
import uuid
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
from services.auth_service import AuthService
from services.audit_service import AuditService

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
from models.audit_log import AuditLog
from models.container_plan import ContainerPlan
from models.container_planning_entry import ContainerPlanningEntry

# Import routers
from api import auth, containers, planning, bookings, packing_workflow, unpacking_workflow, truck_offloading, backload_truck, packing, unpacking, admin, damage_reports, transnet, operational_incidents, audit, container_planning

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


def ensure_booking_schema() -> None:
    with engine.begin() as conn:
        if engine.url.drivername.startswith("sqlite"):
            exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='bookings'")
            ).fetchone()
            if not exists:
                return

            cols = conn.execute(text("PRAGMA table_info(bookings)")).fetchall()
            col_names = {row[1] for row in cols}

            if "booking_type" not in col_names:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN booking_type TEXT NOT NULL DEFAULT 'EXPORT'"))
            if "voyage_number" not in col_names:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN voyage_number TEXT"))
            if "arrival_voyage" not in col_names:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN arrival_voyage TEXT"))
            if "date_in_depot" not in col_names:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN date_in_depot DATETIME"))
            if "category" not in col_names:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN category TEXT"))
            if "notes" not in col_names:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN notes TEXT"))
            return

        if engine.url.drivername.startswith("postgresql"):
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booking_type VARCHAR(20) NOT NULL DEFAULT 'EXPORT'"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS voyage_number VARCHAR(120)"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS arrival_voyage VARCHAR(120)"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS date_in_depot TIMESTAMP"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS category VARCHAR(30)"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS notes TEXT"))


def ensure_container_schema() -> None:
    with engine.begin() as conn:
        if engine.url.drivername.startswith("sqlite"):
            exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='containers'")
            ).fetchone()
            if not exists:
                return

            cols = conn.execute(text("PRAGMA table_info(containers)")).fetchall()
            col_names = {row[1] for row in cols}

            if "manifest_vessel_name" not in col_names:
                conn.execute(text("ALTER TABLE containers ADD COLUMN manifest_vessel_name TEXT"))
            if "manifest_voyage_number" not in col_names:
                conn.execute(text("ALTER TABLE containers ADD COLUMN manifest_voyage_number TEXT"))
            if "depot_list_fcl_count" not in col_names:
                conn.execute(text("ALTER TABLE containers ADD COLUMN depot_list_fcl_count INTEGER"))
            if "depot_list_grp_count" not in col_names:
                conn.execute(text("ALTER TABLE containers ADD COLUMN depot_list_grp_count INTEGER"))
            return

        if engine.url.drivername.startswith("postgresql"):
            conn.execute(text("ALTER TABLE containers ADD COLUMN IF NOT EXISTS manifest_vessel_name VARCHAR(160)"))
            conn.execute(text("ALTER TABLE containers ADD COLUMN IF NOT EXISTS manifest_voyage_number VARCHAR(120)"))
            conn.execute(text("ALTER TABLE containers ADD COLUMN IF NOT EXISTS depot_list_fcl_count INTEGER"))
            conn.execute(text("ALTER TABLE containers ADD COLUMN IF NOT EXISTS depot_list_grp_count INTEGER"))


def ensure_unpacking_schema() -> None:
    with engine.begin() as conn:
        if engine.url.drivername.startswith("sqlite"):
            exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='unpacking_sessions'")
            ).fetchone()
            if not exists:
                return

            cols = conn.execute(text("PRAGMA table_info(unpacking_sessions)")).fetchall()
            col_names = {row[1] for row in cols}

            if "cargo_unloading_started_at" not in col_names:
                conn.execute(text("ALTER TABLE unpacking_sessions ADD COLUMN cargo_unloading_started_at DATETIME"))
            if "cargo_unloading_completed_at" not in col_names:
                conn.execute(text("ALTER TABLE unpacking_sessions ADD COLUMN cargo_unloading_completed_at DATETIME"))
            if "cargo_unloading_duration_minutes" not in col_names:
                conn.execute(text("ALTER TABLE unpacking_sessions ADD COLUMN cargo_unloading_duration_minutes INTEGER"))
            if "manifest_document_reference" not in col_names:
                conn.execute(text("ALTER TABLE unpacking_sessions ADD COLUMN manifest_document_reference TEXT"))
            if "manifest_notes" not in col_names:
                conn.execute(text("ALTER TABLE unpacking_sessions ADD COLUMN manifest_notes TEXT"))
            if "manifest_documented_at" not in col_names:
                conn.execute(text("ALTER TABLE unpacking_sessions ADD COLUMN manifest_documented_at DATETIME"))
            if "manifest_documented_by" not in col_names:
                conn.execute(text("ALTER TABLE unpacking_sessions ADD COLUMN manifest_documented_by TEXT"))
            return

        if engine.url.drivername.startswith("postgresql"):
            conn.execute(text("ALTER TABLE unpacking_sessions ADD COLUMN IF NOT EXISTS cargo_unloading_started_at TIMESTAMP"))
            conn.execute(text("ALTER TABLE unpacking_sessions ADD COLUMN IF NOT EXISTS cargo_unloading_completed_at TIMESTAMP"))
            conn.execute(text("ALTER TABLE unpacking_sessions ADD COLUMN IF NOT EXISTS cargo_unloading_duration_minutes INTEGER"))
            conn.execute(text("ALTER TABLE unpacking_sessions ADD COLUMN IF NOT EXISTS manifest_document_reference VARCHAR(160)"))
            conn.execute(text("ALTER TABLE unpacking_sessions ADD COLUMN IF NOT EXISTS manifest_notes TEXT"))
            conn.execute(text("ALTER TABLE unpacking_sessions ADD COLUMN IF NOT EXISTS manifest_documented_at TIMESTAMP"))
            conn.execute(text("ALTER TABLE unpacking_sessions ADD COLUMN IF NOT EXISTS manifest_documented_by VARCHAR(36)"))


def ensure_packing_schema() -> None:
    with engine.begin() as conn:
        if engine.url.drivername.startswith("sqlite"):
            exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='packing_sessions'")
            ).fetchone()
            if not exists:
                return

            cols = conn.execute(text("PRAGMA table_info(packing_sessions)")).fetchall()
            col_names = {row[1] for row in cols}

            if "condition_report_completed" not in col_names:
                conn.execute(text("ALTER TABLE packing_sessions ADD COLUMN condition_report_completed BOOLEAN NOT NULL DEFAULT 0"))
            if "condition_status" not in col_names:
                conn.execute(text("ALTER TABLE packing_sessions ADD COLUMN condition_status TEXT"))
            if "condition_notes" not in col_names:
                conn.execute(text("ALTER TABLE packing_sessions ADD COLUMN condition_notes TEXT"))
            if "condition_reported_at" not in col_names:
                conn.execute(text("ALTER TABLE packing_sessions ADD COLUMN condition_reported_at DATETIME"))
            if "condition_reported_by" not in col_names:
                conn.execute(text("ALTER TABLE packing_sessions ADD COLUMN condition_reported_by TEXT"))
            return

        if engine.url.drivername.startswith("postgresql"):
            conn.execute(text("ALTER TABLE packing_sessions ADD COLUMN IF NOT EXISTS condition_report_completed BOOLEAN NOT NULL DEFAULT FALSE"))
            conn.execute(text("ALTER TABLE packing_sessions ADD COLUMN IF NOT EXISTS condition_status VARCHAR(30)"))
            conn.execute(text("ALTER TABLE packing_sessions ADD COLUMN IF NOT EXISTS condition_notes TEXT"))
            conn.execute(text("ALTER TABLE packing_sessions ADD COLUMN IF NOT EXISTS condition_reported_at TIMESTAMP"))
            conn.execute(text("ALTER TABLE packing_sessions ADD COLUMN IF NOT EXISTS condition_reported_by VARCHAR(36)"))


# Create database tables
Base.metadata.create_all(bind=engine)
ensure_damage_report_schema()
ensure_booking_schema()
ensure_container_schema()
ensure_unpacking_schema()
ensure_packing_schema()

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
app.include_router(audit.router, prefix="/api")
app.include_router(container_planning.router, prefix="/api")
app.include_router(damage_reports.router, prefix="/api")
app.include_router(transnet.router)
app.include_router(operational_incidents.router, prefix="/api")


def _should_audit_request(path: str, method: str) -> bool:
    if method.upper() == "OPTIONS":
        return False
    if path.startswith("/api/admin/audit"):
        return False
    if path.startswith("/api/health") or path == "/health":
        return False
    if path.startswith("/static") or path.startswith("/uploads"):
        return False

    include_reads = os.getenv("AUDIT_LOG_INCLUDE_READS", "false").lower() in {"1", "true", "yes"}
    if include_reads:
        return path.startswith("/api") or path.startswith("/auth")

    return method.upper() in {"POST", "PUT", "PATCH", "DELETE"} and (
        path.startswith("/api") or path.startswith("/auth")
    )


@app.middleware("http")
async def audit_request_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    status_code = 500
    response = None

    try:
        response = await call_next(request)
        status_code = response.status_code
    finally:
        path = request.url.path
        method = request.method.upper()

        if _should_audit_request(path, method):
            actor = None
            db = None
            try:
                db = SessionLocal()

                bearer = request.headers.get("Authorization", "")
                token = None
                if bearer.lower().startswith("bearer "):
                    token = bearer.split(" ", 1)[1].strip()
                if not token:
                    token = request.cookies.get("access_token")

                if token:
                    try:
                        actor = AuthService.get_user_from_token(token, db)
                    except Exception:
                        actor = None

                AuditService.create_log(
                    db,
                    action=f"{method} {path}",
                    category="http",
                    level="ERROR" if status_code >= 400 else "INFO",
                    message="HTTP request audit event",
                    actor=actor,
                    request_id=request_id,
                    endpoint=path,
                    http_method=method,
                    status_code=status_code,
                    ip_address=request.client.host if request.client else None,
                    metadata={
                        "query": str(request.url.query or ""),
                        "user_agent": request.headers.get("user-agent", ""),
                    },
                )
            except Exception as exc:
                log.error("Failed to persist audit log: %s", exc, exc_info=True)
            finally:
                if db:
                    db.close()

    if response is not None:
        response.headers["X-Request-ID"] = request_id
        return response


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

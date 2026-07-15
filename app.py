import logging
import traceback
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
import sys
from database import initialize_all_databases, get_connection, get_database_name
from waste_manager import get_collection_stats
from ai_engine import get_ai_response
from app_routes import router as advanced_router
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

logger = logging.getLogger("rcpi-waste-ai")
logger.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))
logger.propagate = False

if not logger.handlers:
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

app = FastAPI(title="RCPI Waste AI")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("Incoming request: %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
        logger.info("Response %s for %s %s", response.status_code, request.method, request.url.path)
        return response
    except Exception as exc:
        logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path)
        raise

if (BASE_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Global error handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    error_detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    logger.warning("HTTP exception on %s %s: %s", request.method, request.url.path, error_detail)
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "request": request,
            "status_code": exc.status_code,
            "error": error_detail,
            "path": request.url.path
        },
        status_code=exc.status_code
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "request": request,
            "status_code": 400,
            "error": "Invalid request parameters or query string.",
            "details": exc.errors(),
            "path": request.url.path
        },
        status_code=400
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    tb = traceback.format_exc()
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "request": request,
            "status_code": 500,
            "error": "An unexpected server error occurred.",
            "details": tb,
            "path": request.url.path
        },
        status_code=500
    )

# Include advanced routes
app.include_router(advanced_router)


@app.get('/favicon.ico')
async def favicon():
    icon_path = BASE_DIR / 'static' / 'favicon.ico'
    if icon_path.exists():
        return FileResponse(icon_path, media_type='image/x-icon')
    return Response(status_code=204)


@app.get('/health')
async def health():
    return {'status': 'ok'}


@app.on_event("startup")
async def startup_event():
    db_path = get_database_name()
    logger.info("Starting RCPI Waste AI app")
    logger.info("Python executable: %s", sys.executable)
    logger.info("Database path: %s", db_path)
    logger.info("Current working dir: %s", os.getcwd())
    logger.info("App base dir: %s", BASE_DIR)
    try:
        initialize_all_databases()
        logger.info("Database initialization complete")
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc, exc_info=True)
        raise


# ================= HOME / DASHBOARD =================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    try:
        stats = get_collection_stats()
    except Exception as e:
        print(f"Error getting stats: {e}")
        stats = {"total_waste": 0, "total_collections": 0}
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
        result = cursor.fetchone()
        pending_complaints = result[0] if result else 0
        
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status='Active'")
        result = cursor.fetchone()
        active_vehicles = result[0] if result else 0
        
        cursor.execute("SELECT COUNT(*) FROM wards")
        result = cursor.fetchone()
        total_wards = result[0] if result else 0
        
        conn.close()
    except Exception as e:
        print(f"Error querying database: {e}")
        pending_complaints = 0
        active_vehicles = 0
        total_wards = 0
    
    return templates.TemplateResponse(request, "dashboard.html",
        {
            "request": request,
            "pending_complaints": pending_complaints,
            "active_vehicles": active_vehicles,
            "total_wards": total_wards,
            "total_waste": stats.get("total_waste", 0),
            "total_collections": stats.get("total_collections", 0)
        }
    )


# ================= COMPLAINT PAGE =================

@app.get("/complaints", response_class=HTMLResponse)
async def complaints(request: Request):
    return templates.TemplateResponse(request, "complaint.html",
        {"request": request}
    )


@app.get("/complaint-tracking", response_class=HTMLResponse)
async def complaint_tracking_page(request: Request):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT complaint_id, name, status, priority, assigned_driver, assigned_ward_officer, created_date FROM complaints ORDER BY id DESC")
        complaints = cursor.fetchall()
        conn.close()
    except Exception:
        complaints = []
    return templates.TemplateResponse(request, "complaint_tracking.html", {"request": request, "complaints": complaints})


@app.get("/live-dashboard", response_class=HTMLResponse)
async def live_dashboard(request: Request):
    """Render a polished live operations dashboard for the platform."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
        pending_complaints = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'")
        resolved_complaints = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status='Active'")
        active_vehicles = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM wards")
        total_wards = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(waste_quantity) FROM waste_collection")
        total_waste = cursor.fetchone()[0] or 0

        conn.close()
    except Exception:
        pending_complaints = 0
        resolved_complaints = 0
        active_vehicles = 0
        total_wards = 0
        total_waste = 0

    complaint_pct = min(100, max(0, round((pending_complaints / max(1, total_wards or 1)) * 100, 1)))
    vehicle_pct = min(100, max(0, round((active_vehicles / max(1, total_wards or 1)) * 100, 1)))
    ward_pct = min(100, max(0, round((total_wards / max(1, total_wards or 1)) * 100, 1)))

    return templates.TemplateResponse(
        request,
        "live_dashboard.html",
        {
            "request": request,
            "pending_complaints": pending_complaints,
            "resolved_complaints": resolved_complaints,
            "active_vehicles": active_vehicles,
            "total_wards": total_wards,
            "total_waste": int(total_waste) if total_waste is not None else 0,
            "complaint_pct": complaint_pct,
            "vehicle_pct": vehicle_pct,
            "ward_pct": ward_pct,
        },
    )


# ================= SAVE COMPLAINT =================

@app.post("/complaints", response_class=HTMLResponse)
async def save_complaint(
    request: Request,
    citizen_name: str = Form(...),
    mobile: str = Form(...),
    ward: str = Form(...),
    location: str = Form(...),
    waste_type: str = Form(...),
    complaint: str = Form(...),
    latitude: str = Form(None),
    longitude: str = Form(None),
):
    conn = get_connection()
    cursor = conn.cursor()

    complaint_id = f"CMP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    cursor.execute("""
        INSERT INTO complaints
        (complaint_id,name,mobile,ward,location,waste_type,complaint,status,priority,gps_latitude,gps_longitude)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        complaint_id,
        citizen_name,
        mobile,
        ward,
        location,
        waste_type,
        complaint,
        "Pending",
        "Medium",
        float(latitude) if latitude else None,
        float(longitude) if longitude else None,
    ))

    complaint_row_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return templates.TemplateResponse(request, "success.html",
        {
            "request": request,
            "name": citizen_name,
            "complaint_id": complaint_id,
        }
    )


# ================= WARDS PAGE =================

@app.get("/wards", response_class=HTMLResponse)
async def wards_page(request: Request):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM wards")
    wards = cursor.fetchall()
    conn.close()
    
    return templates.TemplateResponse(request, "wards.html",
        {"request": request, "wards": wards}
    )


@app.post("/wards", response_class=HTMLResponse)
async def add_ward_submit(
    request: Request,
    ward_name: str = Form(...),
    area: str = Form(...),
    email: str = Form(...),
    address: str = Form(...),
    supervisor: str = Form(None),
    population: int = Form(0),
    waste_generation_kg: float = Form(0),
    vehicle_assignment: str = Form(None),
    complaint_count: int = Form(0),
    ward_id: int = Form(None),
):
    conn = get_connection()
    cursor = conn.cursor()

    if ward_id:
        cursor.execute("""
            UPDATE wards
            SET ward_name = ?, area = ?, email = ?, address = ?, supervisor = ?, population = ?, waste_generation_kg = ?, vehicle_assignment = ?, complaint_count = ?
            WHERE id = ?
        """, (ward_name.strip(), area.strip(), email.strip(), address.strip(), (supervisor or "").strip(), population, waste_generation_kg, (vehicle_assignment or "").strip(), complaint_count, ward_id))
    else:
        if not ward_name.strip() or not area.strip() or not email.strip() or not address.strip():
            conn.close()
            return templates.TemplateResponse(request, "error.html", {"request": request, "error": "Ward name, area, email, and address are required."})
        cursor.execute("""
            INSERT INTO wards (ward_name, area, email, address, supervisor, population, waste_generation_kg, vehicle_assignment, complaint_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ward_name.strip(), area.strip(), email.strip(), address.strip(), (supervisor or "").strip(), population, waste_generation_kg, (vehicle_assignment or "").strip(), complaint_count))

    conn.commit()
    conn.close()

    return templates.TemplateResponse(request, "success.html",
        {"request": request, "name": f"Ward {ward_name}"}
    )

@app.post("/wards/delete", response_class=HTMLResponse)
async def delete_ward(request: Request, ward_id: int = Form(...)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM wards WHERE id = ?", (ward_id,))
    conn.commit()
    conn.close()
    return templates.TemplateResponse(request, "success.html", {"request": request, "name": "Ward deleted"})


# ================= VEHICLES PAGE =================

@app.get("/vehicles", response_class=HTMLResponse)
async def vehicles_page(request: Request):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vehicles")
    vehicles = cursor.fetchall()
    conn.close()
    
    return templates.TemplateResponse(request, "vehicles.html",
        {"request": request, "vehicles": vehicles}
    )


@app.post("/vehicles", response_class=HTMLResponse)
async def add_vehicle_submit(
    request: Request,
    vehicle_number: str = Form(...),
    vehicle_type: str = Form(...),
    capacity: int = Form(...),
    driver_name: str = Form(...),
    ward_assigned: str = Form(...),
    route: str = Form(None),
    status: str = Form('Active'),
    vehicle_id: int = Form(None)
):
    conn = get_connection()
    cursor = conn.cursor()

    if vehicle_id:
        cursor.execute("""
            UPDATE vehicles
            SET vehicle_number = ?, vehicle_type = ?, capacity = ?, driver_name = ?, status = ?, ward_assigned = ?, route = ?
            WHERE id = ?
        """, (vehicle_number.strip(), vehicle_type.strip(), capacity, driver_name.strip(), status, ward_assigned.strip(), (route or "").strip(), vehicle_id))
    else:
        if not vehicle_number.strip() or not vehicle_type.strip() or not driver_name.strip() or not ward_assigned.strip():
            conn.close()
            return templates.TemplateResponse(request, "error.html", {"request": request, "error": "Vehicle number, type, driver, and ward assignment are required."})
        cursor.execute("""
            INSERT INTO vehicles (vehicle_number, vehicle_type, capacity, driver_name, status, ward_assigned, route)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (vehicle_number.strip(), vehicle_type.strip(), capacity, driver_name.strip(), status, ward_assigned.strip(), (route or "").strip()))

    conn.commit()
    conn.close()

    return templates.TemplateResponse(request, "success.html",
        {"request": request, "name": f"Vehicle {vehicle_number}"}
    )

@app.post("/vehicles/delete", response_class=HTMLResponse)
async def delete_vehicle(request: Request, vehicle_id: int = Form(...)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
    conn.commit()
    conn.close()
    return templates.TemplateResponse(request, "success.html", {"request": request, "name": "Vehicle deleted"})


# ================= WASTE COLLECTION PAGE =================

@app.get("/waste-collection", response_class=HTMLResponse)
async def waste_collection_page(request: Request):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM waste_collection ORDER BY collection_date DESC")
    collections = cursor.fetchall()
    cursor.execute("SELECT * FROM vehicles")
    vehicles = cursor.fetchall()
    conn.close()
    
    return templates.TemplateResponse(request, "waste_collection.html",
        {"request": request, "collections": collections, "vehicles": vehicles}
    )


@app.post("/waste-collection", response_class=HTMLResponse)
async def add_collection_submit(
    request: Request,
    vehicle_id: int = Form(...),
    ward: str = Form(...),
    waste_quantity: float = Form(...),
    waste_type: str = Form(...)
):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO waste_collection (vehicle_id, ward, waste_quantity, waste_type, status)
        VALUES (?, ?, ?, ?, ?)
    """, (vehicle_id, ward, waste_quantity, waste_type, 'Completed'))
    
    conn.commit()
    conn.close()
    
    return templates.TemplateResponse(request, "success.html",
        {"request": request, "name": "Waste Collection"}
    )


# ================= ADMIN COMPLAINT MANAGEMENT =================

@app.get("/admin-complaints", response_class=HTMLResponse)
async def admin_complaints_page(request: Request):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, complaint_id, name, ward, waste_type, status, priority, assigned_driver, assigned_ward_officer, created_date FROM complaints ORDER BY id DESC")
        complaints = cursor.fetchall()
        conn.close()
    except Exception:
        complaints = []

    return templates.TemplateResponse(request, "admin_complaints.html", {"request": request, "complaints": complaints})


@app.post("/admin-complaints", response_class=HTMLResponse)
async def admin_complaints_update(
    request: Request,
    complaint_id: int = Form(...),
    status: str = Form(None),
    priority: str = Form(None),
    remarks: str = Form(None),
    assigned_driver: str = Form(None),
    assigned_ward_officer: str = Form(None),
):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE complaints
            SET status = ?, priority = ?, remarks = ?, assigned_driver = ?, assigned_ward_officer = ?, updated_date = ?
            WHERE id = ?
        """, (status or "Pending", priority or "Medium", remarks or "", assigned_driver or "", assigned_ward_officer or "", datetime.now().isoformat(), complaint_id))
        conn.commit()
        conn.close()
    except Exception:
        pass

    return RedirectResponse(url="/admin-complaints", status_code=303)

@app.post("/admin-complaints/delete", response_class=HTMLResponse)
async def admin_complaints_delete(request: Request, complaint_id: int = Form(...)):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass
    return RedirectResponse(url="/admin-complaints", status_code=303)


# ================= AI SUPPORT PAGE =================

@app.get("/ai-support", response_class=HTMLResponse)
async def ai_support_page(request: Request):
    return templates.TemplateResponse(request, "ai_support.html",
        {"request": request}
    )


@app.post("/ai-support", response_class=HTMLResponse)
async def ai_support_query(
    request: Request,
    query: str = Form(...),
    image: UploadFile = File(None)
):
    # Use advanced AI engine for response and keep the chat usable even if the engine errors.
    try:
        response_text = get_ai_response(query)
    except Exception:
        response_text = (
            "I can help with waste classification, recycling guidance, disposal steps, "
            "collection advice, and carbon-credit questions. Please ask about a specific item "
            "or waste type such as a plastic bottle, old phone, or hazardous waste."
        )

    if not response_text or not str(response_text).strip():
        response_text = "I can help with waste classification and recycling guidance. Please ask a specific question."

    if image is not None and getattr(image, "filename", None):
        response_text += f"\n\nUploaded image: {image.filename}\n"
        response_text += "Image-based analysis is ready for enhancement. Please describe the item in the chat for detailed guidance."

    return templates.TemplateResponse(request, "ai_support.html",
        {"request": request, "query": query, "response": response_text}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
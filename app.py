from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from starlette.exceptions import HTTPException as StarletteHTTPException
from database import initialize_all_databases, get_connection
from waste_manager import get_collection_stats
from ai_engine import get_ai_response
from app_routes import router as advanced_router

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="RCPI Waste AI")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

if (BASE_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Global error handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    error_detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
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
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "request": request,
            "status_code": 500,
            "error": "An unexpected server error occurred.",
            "details": str(exc),
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
        return FileResponse(icon_path)
    return RedirectResponse('https://fastapi.tiangolo.com/img/favicon.png')


@app.get('/health')
async def health():
    return {'status': 'ok'}


# initialize database (uses central `database.py` schema)
initialize_all_databases()


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


# ================= SAVE COMPLAINT =================

@app.post("/complaints", response_class=HTMLResponse)
async def save_complaint(
    request: Request,
    citizen_name: str = Form(...),
    mobile: str = Form(...),
    ward: str = Form(...),
    location: str = Form(...),
    waste_type: str = Form(...),
    complaint: str = Form(...)
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO complaints
        (name,mobile,ward,location,waste_type,complaint,status)
        VALUES (?,?,?,?,?,?,?)
    """, (
        citizen_name,
        mobile,
        ward,
        location,
        waste_type,
        complaint,
        "Pending"
    ))

    conn.commit()
    conn.close()

    return templates.TemplateResponse(request, "success.html",
        {
            "request": request,
            "name": citizen_name
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
    address: str = Form(...)
):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO wards (ward_name, area, email, address)
        VALUES (?, ?, ?, ?)
    """, (ward_name, area, email, address))
    
    conn.commit()
    conn.close()
    
    return templates.TemplateResponse(request, "success.html",
        {"request": request, "name": f"Ward {ward_name}"}
    )


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
    ward_assigned: str = Form(...)
):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO vehicles (vehicle_number, vehicle_type, capacity, driver_name, status, ward_assigned)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (vehicle_number, vehicle_type, capacity, driver_name, 'Active', ward_assigned))
    
    conn.commit()
    conn.close()
    
    return templates.TemplateResponse(request, "success.html",
        {"request": request, "name": f"Vehicle {vehicle_number}"}
    )


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
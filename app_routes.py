"""
Advanced Routes for RCPI Waste AI System
New functionality for authentication, admin dashboard, reports, and AI features
"""

from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import sqlite3
from datetime import datetime
import json
import os
from database import get_connection, get_database_name

from auth import auth_manager
from esg_scoring import ESGReportGenerator, EnvironmentalScore, SocialScore, GovernanceScore
from carbon_prediction import CarbonPredictionModel
from image_handler import ImageManager, WasteDetector, LocationTracker
from notifications import NotificationManager
from reports import ReportGenerator, PDFReportBuilder, ExcelReportBuilder
from io import BytesIO
try:
    import qrcode
except Exception:
    qrcode = None

BASE_DIR = Path(__file__).resolve().parent
router = APIRouter()
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ==================== AUTHENTICATION ROUTES ====================

@router.get("/admin-login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page"""
    return templates.TemplateResponse(request, "admin_login.html", {"request": request})


@router.post("/admin-login", response_class=HTMLResponse)
async def admin_login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    """Process admin login form"""
    ok, token, user = auth_manager.authenticate_user(username, password)
    if not ok or not token or not user:
        return templates.TemplateResponse(request, "admin_login.html", {"request": request, "error": "Invalid credentials"})

    if user.get('role') != 'admin':
        return templates.TemplateResponse(request, "admin_login.html", {"request": request, "error": "Admin access required"})

    resp = RedirectResponse(url="/admin-dashboard", status_code=303)
    resp.set_cookie("session_token", token, httponly=True, max_age=7*24*3600)
    return resp

@router.get("/citizen-login", response_class=HTMLResponse)
async def citizen_login_page(request: Request):
    """Citizen login page"""
    return templates.TemplateResponse(request, "citizen_login.html", {"request": request})


@router.post("/citizen-register", response_class=HTMLResponse)
async def citizen_register_submit(
    request: Request,
    username: str = Form(None),
    email: str = Form(None),
    password: str = Form(None),
    full_name: str = Form(None),
    phone: str = Form(None),
    address: str = Form(None),
    ward: str = Form(None),
    house_id: str = Form(None),
    gps_location: str = Form(None),
    otp_id: int = Form(None),
    otp_code: str = Form(None),
):
    if otp_id and otp_code:
        ok, message, token, user = auth_manager.verify_registration_otp(otp_id, otp_code)
        if not ok:
            return templates.TemplateResponse(request, "citizen_login.html", {
                "request": request,
                "register_error": message,
                "show_registration_verify_form": True,
                "otp_id": otp_id,
                "phone": None,
                "show_register_form": False,
            })

        resp = RedirectResponse(url="/citizen-dashboard", status_code=303)
        resp.set_cookie("session_token", token, httponly=True, max_age=7*24*3600)
        return resp

    if not (username and email and password and full_name and phone):
        return templates.TemplateResponse(request, "citizen_login.html", {
            "request": request,
            "register_error": "All registration fields are required.",
            "show_register_form": True,
        })

    success, payload = auth_manager.create_registration_otp(
        username=username,
        email=email,
        password=password,
        full_name=full_name,
        phone=phone,
        address=address,
        ward=ward,
        house_id=house_id,
        gps_location=gps_location,
    )
    if not success:
        return templates.TemplateResponse(request, "citizen_login.html", {
            "request": request,
            "register_error": payload.get('error', 'Unable to start registration OTP.'),
            "show_register_form": True,
        })

    return templates.TemplateResponse(request, "citizen_login.html", {
        "request": request,
        "message": f"An OTP has been sent to {phone}. Enter it below to complete registration.",
        "show_registration_verify_form": True,
        "otp_id": payload['otp_id'],
        "phone": phone,
        "show_register_form": False,
    })


# ---------------- Role-specific logins ----------------
@router.get('/supervisor-login', response_class=HTMLResponse)
async def supervisor_login_page(request: Request):
    return templates.TemplateResponse(request, 'admin_login.html', {'request': request, 'title': 'Supervisor Login', 'form_action': '/supervisor-login'})


@router.post('/supervisor-login', response_class=HTMLResponse)
async def supervisor_login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    ok, token, user = auth_manager.authenticate_user(username, password)
    if not ok or not user or user.get('role') != 'supervisor':
        return templates.TemplateResponse(request, 'admin_login.html', {'request': request, 'error': 'Invalid supervisor credentials'})
    resp = RedirectResponse(url='/supervisor-dashboard', status_code=303)
    resp.set_cookie('session_token', token, httponly=True, max_age=7*24*3600)
    return resp


@router.get('/driver-login', response_class=HTMLResponse)
async def driver_login_page(request: Request):
    return templates.TemplateResponse(request, 'admin_login.html', {'request': request, 'title': 'Driver Login', 'form_action': '/driver-login'})


@router.post('/driver-login', response_class=HTMLResponse)
async def driver_login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    ok, token, user = auth_manager.authenticate_user(username, password)
    if not ok or not user or user.get('role') != 'driver':
        return templates.TemplateResponse(request, 'admin_login.html', {'request': request, 'error': 'Invalid driver credentials'})
    resp = RedirectResponse(url='/driver-dashboard', status_code=303)
    resp.set_cookie('session_token', token, httponly=True, max_age=7*24*3600)
    return resp


@router.get('/staff-login', response_class=HTMLResponse)
async def staff_login_page(request: Request):
    return templates.TemplateResponse(request, 'admin_login.html', {'request': request, 'title': 'Staff Login', 'form_action': '/staff-login'})


@router.post('/staff-login', response_class=HTMLResponse)
async def staff_login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    ok, token, user = auth_manager.authenticate_user(username, password)
    if not ok or not user or user.get('role') != 'staff':
        return templates.TemplateResponse(request, 'admin_login.html', {'request': request, 'error': 'Invalid staff credentials'})
    resp = RedirectResponse(url='/staff-dashboard', status_code=303)
    resp.set_cookie('session_token', token, httponly=True, max_age=7*24*3600)
    return resp


@router.post("/citizen-login", response_class=HTMLResponse)
async def citizen_login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    """Process citizen login form"""
    try:
        ok, token, user = auth_manager.authenticate_user(username, password)
    except Exception:
        ok = False
        token = None
        user = None

    if not ok or not token or not user:
        return templates.TemplateResponse(request, "citizen_login.html", {"request": request, "error": "Invalid credentials"})

    # prevent admin using citizen login
    if user.get('role') == 'admin':
        return templates.TemplateResponse(request, "citizen_login.html", {"request": request, "error": "Use admin login for admin accounts"})

    resp = RedirectResponse(url="/citizen-dashboard", status_code=303)
    resp.set_cookie("session_token", token, httponly=True, max_age=7*24*3600)
    return resp

# ==================== ADMIN DASHBOARD ROUTES ====================

@router.get("/admin-dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard with analytics"""
    # Verify session token
    token = request.cookies.get('session_token')
    ok, user = auth_manager.verify_session(token) if token else (False, None)
    if not ok or not user or user.get('role') != 'admin':
        return templates.TemplateResponse(request, "admin_login.html", {"request": request, "error": "Please login as admin"})

    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get statistics
        cursor.execute("SELECT COUNT(*) FROM complaints")
        total_complaints = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
        pending_complaints = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='resolved'")
        resolved_complaints = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status='Active'")
        active_vehicles = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM wards")
        total_wards = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(waste_quantity) FROM waste_collection")
        total_waste = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return templates.TemplateResponse(request, "admin_dashboard.html",
            {
                "request": request,
                "total_complaints": total_complaints,
                "pending_complaints": pending_complaints,
                "resolved_complaints": resolved_complaints,
                "active_vehicles": active_vehicles,
                "total_wards": total_wards,
                "total_waste": int(total_waste)
            }
        )
    except Exception as e:
        return templates.TemplateResponse(request, "admin_dashboard.html", {"request": request, "error": str(e)})


@router.get("/admin-users", response_class=HTMLResponse)
async def admin_users_page(request: Request, role: str = None, search: str = None):
    """Admin user management page with citizen search."""
    token = request.cookies.get('session_token')
    ok, user = auth_manager.verify_session(token) if token else (False, None)
    if not ok or not user or user.get('role') != 'admin':
        return templates.TemplateResponse(request, "admin_login.html", {"request": request, "error": "Please login as admin"})

    query_role = None if role in (None, 'all', '') else role
    users = auth_manager.get_all_users(query_role, search=search)
    return templates.TemplateResponse(request, "admin_users.html", {"request": request, "users": users, "selected_role": role or "all", "search": search or ""})


@router.post("/admin-users", response_class=HTMLResponse)
async def admin_users_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(None),
    phone: str = Form(None),
    role: str = Form(...)
):
    token = request.cookies.get('session_token')
    ok, user = auth_manager.verify_session(token) if token else (False, None)
    if not ok or not user or user.get('role') != 'admin':
        return templates.TemplateResponse(request, "admin_login.html", {"request": request, "error": "Please login as admin"})

    success, message = auth_manager.register_user(username, email, password, full_name or "", phone or "", role=role)
    users = auth_manager.get_all_users()
    return templates.TemplateResponse(request, "admin_users.html",
        {"request": request, "users": users, "message": message, "selected_role": "all"}
    )


@router.post("/admin-users-action", response_class=HTMLResponse)
async def admin_users_action(request: Request, user_id: int = Form(...), action: str = Form(...)):
    token = request.cookies.get('session_token')
    ok, current_user = auth_manager.verify_session(token) if token else (False, None)
    if not ok or not current_user or current_user.get('role') != 'admin':
        return templates.TemplateResponse(request, "admin_login.html", {"request": request, "error": "Please login as admin"})

    message = "Action completed successfully."
    if action == 'activate':
        auth_manager.set_user_active_status(user_id, True)
        message = "User activated successfully."
    elif action == 'deactivate':
        auth_manager.set_user_active_status(user_id, False)
        message = "User deactivated successfully."
    elif action == 'delete':
        auth_manager.delete_user(user_id)
        message = "User deleted successfully."
    elif action == 'reset_password':
        auth_manager.reset_user_password(user_id, 'RCPI@2026')
        message = "Password reset completed."
    else:
        message = "Unknown action."

    users = auth_manager.get_all_users()
    return templates.TemplateResponse(request, "admin_users.html",
        {"request": request, "users": users, "message": message, "selected_role": "all"}
    )


@router.get("/citizen-dashboard", response_class=HTMLResponse)
async def citizen_dashboard(request: Request):
    """Citizen dashboard with personal tracking"""
    token = request.cookies.get('session_token')
    ok, user = auth_manager.verify_session(token) if token else (False, None)
    if not ok or not user:
        return templates.TemplateResponse(request, "citizen_login.html", {"request": request, "error": "Please login"})
    if user.get('role') != 'citizen':
        return templates.TemplateResponse(request, "citizen_login.html", {"request": request, "error": "Citizen access required"})

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, complaint_id, status, waste_type, location, created_date FROM complaints WHERE user_id = ? ORDER BY id DESC", (user['user_id'],))
        complaints = cursor.fetchall()

        try:
            cursor.execute("SELECT SUM(waste_quantity) FROM waste_collection WHERE ward = (SELECT ward FROM citizens WHERE user_id = ?)", (user['user_id'],))
            total_waste = cursor.fetchone()[0] or 0
        except Exception:
            total_waste = 0

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE user_id = ?", (user['user_id'],))
        complaint_count = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE user_id = ? AND LOWER(status) = 'resolved'", (user['user_id'],))
        resolved_count = cursor.fetchone()[0] or 0

        cursor.execute("SELECT address, ward, house_id, gps_location FROM citizens WHERE user_id = ?", (user['user_id'],))
        citizen_profile = cursor.fetchone() or (None, None, None, None)

        cursor.execute("SELECT collection_date, waste_type, waste_quantity FROM citizen_waste_history WHERE user_id = ? ORDER BY collection_date DESC LIMIT 10", (user['user_id'],))
        waste_history = cursor.fetchall()
        conn.close()
    except Exception:
        complaints = []
        total_waste = 0
        complaint_count = 0
        resolved_count = 0
        citizen_profile = (None, None, None, None)
        waste_history = []

    return templates.TemplateResponse(request, "citizen_dashboard.html", {
        "request": request,
        "user": user,
        "complaints": complaints,
        "total_waste": int(total_waste),
        "complaint_count": complaint_count,
        "resolved_count": resolved_count,
        "citizen_profile": citizen_profile,
        "waste_history": waste_history,
    })


@router.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    token = request.cookies.get('session_token')
    if token:
        auth_manager.logout_user(token)

    resp = templates.TemplateResponse(request, "index.html", {"request": request, "msg": "Logged out"})
    resp.delete_cookie('session_token')
    return resp


# ==================== IMAGE UPLOAD & AI DETECTION ====================

@router.get("/image-upload", response_class=HTMLResponse)
async def image_upload_page(request: Request):
    """Image upload page for waste detection"""
    return templates.TemplateResponse(request, "image_upload.html", {"request": request})


@router.get("/api/detect-waste", response_class=HTMLResponse)
async def detect_waste_page(request: Request):
    """Serve the detection upload page for GET requests."""
    return templates.TemplateResponse(request, "image_upload.html", {"request": request})


@router.post("/api/detect-waste")
async def detect_waste(
    request: Request,
    image: UploadFile = File(...),
    latitude: float = None,
    longitude: float = None,
    description: str = None
):
    """Detect waste category from uploaded image"""
    try:
        # Read file
        content = await image.read()
        
        # Save image
        success, image_id = ImageManager.save_image(
            content, 
            image.filename,
            user_id=1,
            gps_lat=latitude,
            gps_lon=longitude
        )
        
        if not success:
            return JSONResponse({"error": image_id})
        
        # Analyze image
        success, result = WasteDetector.analyze_image(int(image_id))
        
        return JSONResponse(result)
    
    except Exception as e:
        return JSONResponse({"error": str(e)})


# ==================== REPORTS & EXPORT ====================

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "citizen_login.html", {"request": request, "forgot_password": True, "show_reset_form": False})


@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password_submit(request: Request, username: str = Form(...)):
    user = auth_manager.get_user_by_identifier(username)
    if not user:
        return templates.TemplateResponse(request, "citizen_login.html", {"request": request, "error": "No account found for that username or email.", "forgot_password": True, "show_reset_form": False})

    success, payload = auth_manager.create_password_reset_token(user['id'])
    if not success or not payload:
        return templates.TemplateResponse(request, "citizen_login.html", {"request": request, "error": "Unable to generate reset code right now.", "forgot_password": True, "show_reset_form": False})

    return templates.TemplateResponse(request, "citizen_login.html", {
        "request": request,
        "message": "A verification code has been sent to your registered mobile number. Enter it below to reset your password.",
        "forgot_password": True,
        "show_reset_form": True,
    })


@router.post("/reset-password", response_class=HTMLResponse)
async def reset_password_submit(request: Request, token: str = Form(...), password: str = Form(...)):
    if not token or not password:
        return templates.TemplateResponse(request, "citizen_login.html", {"request": request, "error": "A reset code and new password are required.", "forgot_password": True, "show_reset_form": True})

    if auth_manager.reset_password_with_token(token, password):
        return templates.TemplateResponse(request, "citizen_login.html", {"request": request, "message": "Password reset successful. Please log in with your new password.", "forgot_password": False})

    return templates.TemplateResponse(request, "citizen_login.html", {"request": request, "error": "Invalid or expired reset code.", "forgot_password": True, "show_reset_form": True})


@router.get("/admin-citizen-complaints/{user_id}", response_class=HTMLResponse)
async def admin_citizen_complaints(request: Request, user_id: int):
    token = request.cookies.get('session_token')
    ok, current_user = auth_manager.verify_session(token) if token else (False, None)
    if not ok or not current_user or current_user.get('role') != 'admin':
        return templates.TemplateResponse(request, "admin_login.html", {"request": request, "error": "Please login as admin"})

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, email, full_name, phone FROM users WHERE id = ?", (user_id,))
    user_row = cursor.fetchone()
    cursor.execute("SELECT id, complaint_id, status, waste_type, location, created_date FROM complaints WHERE user_id = ? ORDER BY id DESC", (user_id,))
    complaints = cursor.fetchall()
    conn.close()

    return templates.TemplateResponse(request, "admin_citizen_history.html", {
        "request": request,
        "citizen": user_row,
        "complaints": complaints,
    })


@router.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    """Reports page"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT SUM(waste_quantity) FROM waste_collection")
            total_waste = cursor.fetchone()[0] or 0
        except Exception:
            total_waste = 0

        try:
            cursor.execute("SELECT LOWER(status), COUNT(*) FROM complaints GROUP BY LOWER(status)")
            complaint_stats = cursor.fetchall() or []
        except Exception:
            complaint_stats = []

        try:
            cursor.execute("SELECT waste_type, SUM(waste_quantity) FROM waste_collection GROUP BY waste_type")
            waste_stats = cursor.fetchall() or []
        except Exception:
            waste_stats = []

        try:
            cursor.execute("SELECT COUNT(*) FROM households")
            total_households = cursor.fetchone()[0] or 0
        except Exception:
            total_households = 0

        try:
            cursor.execute("SELECT COUNT(*) FROM users WHERE role IN ('driver','staff','supervisor')")
            total_staff = cursor.fetchone()[0] or 0
        except Exception:
            total_staff = 0

        try:
            cursor.execute("SELECT COUNT(*) FROM complaints WHERE LOWER(status) IN ('resolved','closed')")
            resolved_complaints = cursor.fetchone()[0] or 0
        except Exception:
            resolved_complaints = 0

        try:
            cursor.execute("SELECT COALESCE(SUM(waste_quantity),0) FROM waste_collection")
            waste_collected = cursor.fetchone()[0] or 0
        except Exception:
            waste_collected = 0

        conn.close()

    except Exception:
        total_waste = 0
        complaint_stats = []
        waste_stats = []
        total_households = 0
        total_staff = 0
        resolved_complaints = 0
        waste_collected = 0

    return templates.TemplateResponse(request, "reports.html", {
        "request": request,
        "total_waste": int(total_waste),
        "complaint_stats": complaint_stats,
        "waste_stats": waste_stats,
        "total_households": total_households,
        "total_staff": total_staff,
        "resolved_complaints": resolved_complaints,
        "waste_collected": int(waste_collected),
    })


@router.get("/api/reports/{report_type}")
async def download_report(report_type: str, format: str = "pdf"):
    """Download report in specified format"""
    try:
        if report_type == "complaints":
            data = ReportGenerator.get_complaint_summary()
        elif report_type == "waste":
            data = ReportGenerator.get_waste_summary()
        elif report_type == "esg":
            data = ESGReportGenerator.generate_report()
        else:
            return JSONResponse({"error": "Unknown report type"})
        # If generator returned an error dict, surface it to the UI
        if isinstance(data, dict) and data.get('error'):
            return HTMLResponse(f"<h1>Report Error</h1><pre>{data.get('error')}</pre>")
        
        if format == "pdf":
            pdf_content = PDFReportBuilder.generate_pdf_report(report_type, data)
            if pdf_content:
                return StreamingResponse(
                    iter([pdf_content]),
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=\"{report_type}_report.pdf\""}
                )
        elif format == "excel":
            excel_content = ExcelReportBuilder.generate_excel_report(report_type, data)
            if excel_content:
                return StreamingResponse(
                    iter([excel_content]),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=\"{report_type}_report.xlsx\""}
                )
        elif format == "csv":
            csv_content = ReportGenerator.generate_csv_report(report_type, data)
            return StreamingResponse(
                iter([csv_content.encode()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=\"{report_type}_report.csv\""}
            )
        
        # Fallback to HTML
        html_content = ReportGenerator.generate_html_report(report_type, data)
        return HTMLResponse(html_content)
    
    except Exception as e:
        return HTMLResponse(f"<h1>Report Error</h1><pre>{str(e)}</pre>")


# ==================== ESG & ENVIRONMENTAL ====================

@router.get("/households", response_class=HTMLResponse)
async def households_page(request: Request):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, house_id, citizen_name, mobile, address, ward, family_members FROM households ORDER BY id DESC")
    households = cursor.fetchall()
    conn.close()
    return templates.TemplateResponse(request, "households.html", {"request": request, "households": households})


@router.post("/households", response_class=HTMLResponse)
async def households_submit(request: Request, house_id: str = Form(...), citizen_name: str = Form(...), mobile: str = Form(...), address: str = Form(...), ward: str = Form(...), family_members: int = Form(1)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO households (house_id, citizen_name, mobile, address, ward, family_members) VALUES (?, ?, ?, ?, ?, ?)", (house_id, citizen_name, mobile, address, ward, family_members))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/households", status_code=303)


@router.get("/staff-management", response_class=HTMLResponse)
async def staff_management_page(request: Request):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT u.username, u.full_name, u.role, s.ward FROM users u LEFT JOIN staff s ON s.user_id = u.id WHERE u.role IN ('staff','driver','supervisor') ORDER BY u.id DESC")
    staff = cursor.fetchall()
    conn.close()
    return templates.TemplateResponse(request, "staff_management.html", {"request": request, "staff": staff})


@router.get("/esg-report", response_class=HTMLResponse)
async def esg_report_page(request: Request):
    """ESG report page"""
    try:
        report = ESGReportGenerator.generate_report()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ESG Report - RCPI Waste AI</title>
            <style>
                body {{ font-family: Arial; margin: 40px; background: #f5f5f5; }}
                .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                h1 {{ color: #667eea; }}
                .score-card {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; text-align: center; margin: 20px 0; border-radius: 10px; }}
                .score-value {{ font-size: 48px; font-weight: bold; }}
                .recommendation {{ background: #f0f4ff; padding: 15px; margin: 10px 0; border-left: 4px solid #667eea; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🌍 ESG Performance Report</h1>
                
                <div class="score-card">
                    <h2>Environmental Score</h2>
                    <div class="score-value">{report.get('environmental_score', 0)}</div>
                </div>
                
                <div class="score-card" style="background: linear-gradient(135deg, #f093fb, #f5576c);">
                    <h2>Social Score</h2>
                    <div class="score-value">{report.get('social_score', 0)}</div>
                </div>
                
                <div class="score-card" style="background: linear-gradient(135deg, #4facfe, #00f2fe);">
                    <h2>Governance Score</h2>
                    <div class="score-value">{report.get('governance_score', 0)}</div>
                </div>
                
                <div class="score-card" style="background: linear-gradient(135deg, #43e97b, #38f9d7);">
                    <h2>Overall ESG Score</h2>
                    <div class="score-value">{report.get('esg_score', 0)}</div>
                </div>
                
                <h3>💡 Recommendations</h3>
                {''.join([f'<div class="recommendation">{rec}</div>' for rec in report.get('recommendations', [])])}
                
                <h3>♻️ Carbon Metrics</h3>
                <p><strong>Total CO2 Saved:</strong> {report.get('carbon_metrics', {}).get('total_co2_saved_kg', 0)} kg</p>
                <p><strong>Carbon Credits:</strong> {report.get('carbon_metrics', {}).get('carbon_credits_earned', 0)}</p>
                <p><strong>Credit Value:</strong> ${report.get('carbon_metrics', {}).get('carbon_credit_value_usd', 0)}</p>
            </div>
        </body>
        </html>
        """
        return html
    
    except Exception as e:
        return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>"


# ==================== CARBON PREDICTIONS ====================

@router.get("/carbon-predictions")
async def carbon_predictions_page():
    """Carbon prediction page"""
    try:
        predictions = CarbonPredictionModel.predict_carbon_emissions(days_ahead=30)
        per_capita = CarbonPredictionModel.predict_carbon_footprint_per_citizen()
        savings = CarbonPredictionModel.predict_co2_savings_potential()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Carbon Predictions - RCPI Waste AI</title>
            <style>
                body {{ font-family: Arial; margin: 40px; background: #f5f5f5; }}
                .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                h1, h2 {{ color: #667eea; }}
                .metric {{ background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .metric-label {{ font-weight: bold; color: #667eea; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔮 Carbon Emission Predictions</h1>
                
                <h2>30-Day Forecast</h2>
                <div class="metric">
                    <div class="metric-label">Predicted Waste (kg)</div>
                    <p>{predictions.get('total_waste_predicted_kg', 0)}</p>
                </div>
                <div class="metric">
                    <div class="metric-label">Predicted Carbon (kg CO2)</div>
                    <p>{predictions.get('total_carbon_predicted_kg', 0)}</p>
                </div>
                <div class="metric">
                    <div class="metric-label">Daily Average Waste</div>
                    <p>{predictions.get('daily_average_waste_kg', 0)} kg</p>
                </div>
                
                <h2>Per Capita Analysis</h2>
                <div class="metric">
                    <div class="metric-label">Per Citizen Monthly</div>
                    <p>{per_capita.get('per_capita_carbon_kg', 0)} kg</p>
                </div>
                <div class="metric">
                    <div class="metric-label">Status</div>
                    <p>{per_capita.get('status', 'N/A')}</p>
                </div>
                
                <h2>Improvement Scenarios</h2>
                {''.join([f'''<div class="metric">
                    <div class="metric-label">{scenario}: {data.get('description', '')}</div>
                    <p>Predicted Carbon: {data.get('predicted_carbon_kg', 0)} kg</p>
                    <p>Savings: {data.get('carbon_savings_kg', 0)} kg ({data.get('carbon_savings_percent', 0)}%)</p>
                </div>''' for scenario, data in savings.get('scenarios', {}).items()])}
            </div>
        </body>
        </html>
        """
        return HTMLResponse(html)
    
    except Exception as e:
        return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>"


# ==================== LOCATION & HOTSPOTS ====================

@router.get("/api/hotspots")
async def get_hotspots(radius: float = 1.0):
    """Get waste hotspots"""
    hotspots = LocationTracker.get_user_location_history()
    return JSONResponse({"hotspots": hotspots})


# ==================== LANDFILL DATA ====================
def ensure_landfill_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS landfill_sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            latitude REAL,
            longitude REAL,
            capacity_tons REAL,
            status TEXT,
            last_inspection TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


@router.get("/landfill-data", response_class=HTMLResponse)
async def landfill_data_page(request: Request):
    ensure_landfill_table()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, latitude, longitude, capacity_tons, status FROM landfill_sites")
    sites = cursor.fetchall()
    conn.close()

    html = """
    <html><body><h1>Landfill Sites</h1><table border='1'><tr><th>ID</th><th>Name</th><th>Lat</th><th>Lon</th><th>Capacity (t)</th><th>Status</th></tr>
    """
    for s in sites:
        html += f"<tr><td>{s[0]}</td><td>{s[1]}</td><td>{s[2]}</td><td>{s[3]}</td><td>{s[4]}</td><td>{s[5]}</td></tr>"
    html += "</table></body></html>"
    return HTMLResponse(html)


# ==================== QR CODE FOR BINS ====================
@router.get('/qr-bin', response_class=HTMLResponse)
async def qr_bin_page(request: Request):
    html = """
    <html><body>
    <h1>Generate QR for Waste Bin</h1>
    <form method='GET' action='/generate-qr'>
    Bin ID: <input name='bin_id' required /> <button type='submit'>Generate QR</button>
    </form>
    </body></html>
    """
    return HTMLResponse(html)


@router.get('/generate-qr')
async def generate_qr(bin_id: str):
    data = f"bin:{bin_id}"
    if qrcode is None:
        return JSONResponse({'error': 'qrcode library not installed'})
    img = qrcode.make(data)
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return StreamingResponse(buf, media_type='image/png')


# ---------------- Backup system ----------------
def create_backup_copy():
    backups_dir = Path('backups')
    backups_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    src = Path(get_database_name())
    dst = backups_dir / f'waste_ai_backup_{timestamp}.db'
    try:
        import shutil
        shutil.copy2(src, dst)
        return True, str(dst)
    except Exception as e:
        return False, str(e)


@router.get('/create-backup')
async def create_backup():
    ok, info = create_backup_copy()
    if not ok:
        return JSONResponse({'error': info})
    return JSONResponse({'backup_path': info})


@router.get('/backup-db')
async def download_backup():
    backups_dir = Path('backups')
    files = sorted(backups_dir.glob('waste_ai_backup_*.db'), reverse=True)
    if not files:
        return JSONResponse({'error': 'No backups available'})
    latest = files[0]
    return FileResponse(path=str(latest), filename=latest.name, media_type='application/octet-stream')


# ==================== VEHICLE TRACKING & ROUTE OPTIMIZATION ====================
@router.get('/vehicle-tracking', response_class=HTMLResponse)
async def vehicle_tracking_page(request: Request):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, vehicle_number, status, ward_assigned, route, driver_name, daily_collection_kg FROM vehicles ORDER BY id')
    vehicles = cursor.fetchall()
    conn.close()

    rows = []
    for vehicle in vehicles:
        rows.append({
            'id': vehicle[0],
            'vehicle_number': vehicle[1],
            'status': vehicle[2] or 'Unknown',
            'ward_assigned': vehicle[3] or 'Unassigned',
            'route': vehicle[4] or 'Pending',
            'driver_name': vehicle[5] or 'N/A',
            'daily_collection_kg': vehicle[6] or 0,
        })

    html = """
    <!doctype html>
    <html>
    <head>
    <title>Live Vehicle Tracking</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; margin-top: 12px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #f4f4f4; }
        .status { font-weight: bold; }
    </style>
    </head>
    <body>
    <h1>Live Vehicle Tracking</h1>
    <p>Operational overview from the vehicle database.</p>
    <table>
        <tr><th>Vehicle</th><th>Status</th><th>Ward</th><th>Route</th><th>Driver</th><th>Daily Collection (kg)</th></tr>
    """
    for row in rows:
        html += f"<tr><td>{row['vehicle_number']}</td><td class='status'>{row['status']}</td><td>{row['ward_assigned']}</td><td>{row['route']}</td><td>{row['driver_name']}</td><td>{row['daily_collection_kg']}</td></tr>"
    html += """
    </table>
    </body></html>
    """
    return HTMLResponse(html)


@router.get('/api/vehicles')
async def api_vehicles():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, vehicle_number, status, ward_assigned FROM vehicles')
    rows = cursor.fetchall()
    conn.close()
    vehicles = []
    for r in rows:
        vehicles.append({'id': r[0], 'vehicle_number': r[1], 'status': r[2], 'ward_assigned': r[3], 'latitude': None, 'longitude': None})
    return JSONResponse({'vehicles': vehicles})


@router.get('/route-optimization', response_class=HTMLResponse)
async def route_opt_page(request: Request):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT vehicle_number, ward_assigned, route, status FROM vehicles WHERE status = ? ORDER BY id', ('Active',))
    active_vehicles = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) FROM wards')
    ward_count = cursor.fetchone()[0] or 0
    conn.close()

    html = f"""
    <html><body>
    <h1>Route Recommendation</h1>
    <p>Active vehicles: {len(active_vehicles)}</p>
    <p>Registered wards: {ward_count}</p>
    <ul>
    """
    for vehicle in active_vehicles:
        html += f"<li>{vehicle[0]} -> {vehicle[1]} via {vehicle[2]}</li>"
    html += """
    </ul>
    <p>Suggested action: prioritize wards with the highest complaint density and assign the nearest active vehicle.</p>
    </body></html>
    """
    return HTMLResponse(html)


# ---------------- Carbon Calculators & Dashboard ----------------
@router.get('/carbon-calculator', response_class=HTMLResponse)
async def carbon_calculator_page(request: Request):
    html = '''
    <html><body>
    <h1>CO2 Saved Calculator</h1>
    <form method="POST" action="/carbon-calc">
    Waste collected (kg): <input name="waste_kg" required type="number" step="0.1" /><br>
    Diversion efficiency (%): <input name="efficiency" required type="number" step="0.1" value="75" /><br>
    <button type="submit">Calculate CO2 Saved</button>
    </form>
    </body></html>
    '''
    return HTMLResponse(html)


@router.post('/carbon-calc')
async def carbon_calc(waste_kg: float = Form(...), efficiency: float = Form(...)):
    # Simple emission factor (kg CO2 per kg waste avoided) — conservative estimate
    emission_factor = 0.21
    diverted = waste_kg * (efficiency / 100.0)
    co2_saved_kg = diverted * emission_factor
    credits = co2_saved_kg / 1000.0
    price_per_tonne = 15.0
    est_value_usd = credits * price_per_tonne
    html = f"""<html><body><h1>CO2 Saved Result</h1><p>Waste diverted: {diverted:.2f} kg</p><p>CO2 saved: {co2_saved_kg:.2f} kg</p><p>Estimated carbon credits: {credits:.3f} t</p><p>Estimated value: ${est_value_usd:.2f}</p><a href='/carbon-dashboard'>View Carbon Dashboard</a></body></html>"""
    return HTMLResponse(html)


@router.get('/carbon-dashboard', response_class=HTMLResponse)
async def carbon_dashboard(request: Request):
    # Aggregate simple metrics from waste_collection table
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(waste_quantity) FROM waste_collection')
    total_waste = cursor.fetchone()[0] or 0
    conn.close()
    # Use same emission factor
    emission_factor = 0.21
    # Assume 60% diversion overall for dashboard
    diversion_pct = 60.0
    co2_saved_kg = total_waste * (diversion_pct/100.0) * emission_factor
    credits = co2_saved_kg / 1000.0
    html = f"""
    <html><body><h1>Carbon Project Dashboard</h1>
    <p>Total waste recorded: {total_waste} kg</p>
    <p>Estimated CO2 saved (at {diversion_pct}% diversion): {co2_saved_kg:.2f} kg</p>
    <p>Estimated carbon credits: {credits:.3f} t</p>
    </body></html>
    """
    return HTMLResponse(html)


# ---------------- Role dashboards ----------------
def _verify_role(request: Request, role: str):
    token = request.cookies.get('session_token')
    ok, user = auth_manager.verify_session(token) if token else (False, None)
    return ok and user and user.get('role') == role, user


@router.get('/supervisor-dashboard', response_class=HTMLResponse)
async def supervisor_dashboard(request: Request):
    ok, user = _verify_role(request, 'supervisor')
    if not ok:
        return templates.TemplateResponse(request, 'supervisor_login.html' if Path('templates/supervisor_login.html').exists() else 'admin_login.html', {'request': request, 'error': 'Please login as supervisor'})

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status IN ('Assigned', 'In Progress', 'Verified')")
    active = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Resolved'")
    resolved = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM vehicles")
    vehicles = cursor.fetchone()[0] or 0
    conn.close()
    return templates.TemplateResponse(request, 'admin_dashboard.html', {'request': request, 'user': user, 'total_complaints': active, 'pending_complaints': active, 'resolved_complaints': resolved, 'active_vehicles': vehicles, 'total_wards': 0, 'total_waste': 0})


@router.get('/driver-dashboard', response_class=HTMLResponse)
async def driver_dashboard(request: Request):
    ok, user = _verify_role(request, 'driver')
    if not ok:
        return templates.TemplateResponse(request, 'admin_login.html', {'request': request, 'error': 'Please login as driver'})

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, complaint_id, ward, waste_type, status FROM complaints WHERE assigned_driver = ? OR assigned_driver IS NULL ORDER BY id DESC LIMIT 10", (user.get('username') or '',))
    complaints = cursor.fetchall()
    conn.close()
    return templates.TemplateResponse(request, 'admin_dashboard.html', {'request': request, 'user': user, 'complaints': complaints, 'total_complaints': len(complaints), 'pending_complaints': len(complaints), 'resolved_complaints': 0, 'active_vehicles': 0, 'total_wards': 0, 'total_waste': 0})


@router.get('/staff-dashboard', response_class=HTMLResponse)
async def staff_dashboard(request: Request):
    ok, user = _verify_role(request, 'staff')
    if not ok:
        return templates.TemplateResponse(request, 'admin_login.html', {'request': request, 'error': 'Please login as staff'})

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, complaint_id, ward, waste_type, status FROM complaints WHERE assigned_staff = ? OR assigned_driver = ? ORDER BY id DESC LIMIT 10", (user.get('username') or '', user.get('username') or ''))
    complaints = cursor.fetchall()
    conn.close()
    return templates.TemplateResponse(request, 'admin_dashboard.html', {'request': request, 'user': user, 'complaints': complaints, 'total_complaints': len(complaints), 'pending_complaints': len(complaints), 'resolved_complaints': 0, 'active_vehicles': 0, 'total_wards': 0, 'total_waste': 0})


@router.post('/staff-task-update', response_class=HTMLResponse)
async def staff_task_update(
    request: Request,
    complaint_id: int = Form(...),
    status: str = Form(...),
    remarks: str = Form(None),
):
    ok, user = _verify_role(request, 'staff')
    if not ok:
        return templates.TemplateResponse(request, 'admin_login.html', {'request': request, 'error': 'Please login as staff'})

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE complaints SET status = ?, remarks = ?, updated_date = ? WHERE id = ?",
        (status, remarks or '', datetime.now().isoformat(), complaint_id),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url='/staff-dashboard', status_code=303)


@router.post('/staff-proof-upload', response_class=HTMLResponse)
async def staff_proof_upload(
    request: Request,
    complaint_id: int = Form(...),
    proof_note: str = Form(None),
    proof_file: UploadFile = File(None),
):
    ok, user = _verify_role(request, 'staff')
    if not ok:
        return templates.TemplateResponse(request, 'admin_login.html', {'request': request, 'error': 'Please login as staff'})

    proof_path = None
    if proof_file is not None and getattr(proof_file, 'filename', None):
        upload_dir = BASE_DIR / 'static' / 'uploads'
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{Path(proof_file.filename).name}"
        file_path = upload_dir / safe_name
        file_path.write_bytes(await proof_file.read())
        proof_path = f'/static/uploads/{safe_name}'

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE complaints SET remarks = ?, image_path = ?, updated_date = ? WHERE id = ?",
        ((proof_note or '') + (f' | Proof: {proof_path}' if proof_path else ''), proof_path, datetime.now().isoformat(), complaint_id),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url='/staff-dashboard', status_code=303)


# ==================== ANALYTICS ====================

@router.get("/admin-analytics", response_class=HTMLResponse)
async def admin_analytics(request: Request):
    """Admin analytics page"""
    return templates.TemplateResponse(request, "admin_dashboard.html", {"request": request})


# ==================== NOTIFICATION PREFERENCES ====================

@router.get("/notification-preferences", response_class=HTMLResponse)
async def notification_preferences_page(request: Request):
    """Notification preferences page"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Notification Preferences - RCPI Waste AI</title>
        <style>
            body { font-family: Arial; margin: 40px; background: #f5f5f5; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            h1 { color: #667eea; }
            .pref-group { margin: 20px 0; }
            label { display: flex; align-items: center; margin: 10px 0; }
            input[type="checkbox"] { margin-right: 10px; }
            button { background: #667eea; color: white; padding: 10px 20px; cursor: pointer; border: none; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔔 Notification Preferences</h1>
            <form>
                <div class="pref-group">
                    <h3>Notification Channels</h3>
                    <label><input type="checkbox" checked> Email Notifications</label>
                    <label><input type="checkbox"> SMS Notifications</label>
                    <label><input type="checkbox"> WhatsApp Notifications</label>
                </div>
                
                <div class="pref-group">
                    <h3>Alert Types</h3>
                    <label><input type="checkbox" checked> Complaint Status Updates</label>
                    <label><input type="checkbox" checked> Collection Schedule</label>
                    <label><input type="checkbox" checked> Emergency Alerts</label>
                </div>
                
                <button type="submit">💾 Save Preferences</button>
            </form>
        </div>
    </body>
    </html>
    """
    return html

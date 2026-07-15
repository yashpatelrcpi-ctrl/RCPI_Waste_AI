# RCPI Waste AI Deployment Guide

## Overview
RCPI Waste AI is a FastAPI-based smart waste management platform with AI-assisted waste guidance, complaint workflows, vehicle and ward management, reporting, and role-based access.

## Prerequisites
- Python 3.11+
- A Render account for deployment
- GitHub repository access

## Local Development
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python -m uvicorn app:app --host 127.0.0.1 --port 8000
   ```
4. Open the app at http://127.0.0.1:8000/.

## Production Deployment on Render
1. Connect this repository to Render.
2. Use the existing Render configuration in render.yaml.
3. Render will run:
   - Build: `pip install -r requirements.txt`
   - Start: `python -m uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Set the environment variable `WASTE_DB_PATH=/tmp/waste_ai.db` for persistence.
5. Confirm health at `/health`.

## Demo Accounts
- Admin: admin / admin@123
- Citizen: test_citizen / citizen@123
- Supervisor: supervisor / supervisor@123
- Driver: driver1 / driver@123
- Staff: staff1 / staff@123

## Notes
- The application writes logs to the logs/app.log file.
- The SQLite database is initialized automatically on startup.

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")

DEFAULT_DB_PATH = os.getenv("WASTE_DB_PATH")
if DEFAULT_DB_PATH:
    DATABASE_NAME = DEFAULT_DB_PATH
else:
    DATABASE_NAME = str(BASE_DIR / "waste_ai.db")


def get_database_name():
    env_db = os.getenv("WASTE_DB_PATH")
    if env_db:
        try:
            env_path = Path(env_db)
            if not env_path.is_absolute():
                env_path = BASE_DIR / env_path
            env_path = env_path.resolve()
            _ensure_database_directory(str(env_path))
            return str(env_path)
        except Exception:
            pass

    return str(BASE_DIR / "waste_ai.db")


def _ensure_database_directory(db_name: str):
    db_path = Path(db_name)
    parent_dir = db_path.parent
    if parent_dir and not parent_dir.exists():
        try:
            parent_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            print(f"Failed to create database directory {parent_dir}: {exc}")
            raise


def _use_postgres() -> bool:
    return bool(DATABASE_URL)


def _id_column_definition() -> str:
    return "SERIAL PRIMARY KEY" if _use_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"


def get_connection():
    if _use_postgres():
        try:
            import psycopg2
        except Exception:
            print("psycopg2 not available; falling back to SQLite")
            db_name = get_database_name()
            _ensure_database_directory(db_name)
            return sqlite3.connect(db_name, timeout=30, detect_types=sqlite3.PARSE_DECLTYPES)

        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn

    db_name = get_database_name()
    _ensure_database_directory(db_name)
    return sqlite3.connect(db_name, timeout=30, detect_types=sqlite3.PARSE_DECLTYPES)


def reset_database():
    """Delete existing database to recreate with new schema"""
    db_name = get_database_name()
    if os.path.exists(db_name):
        os.remove(db_name)
        print(f"Old database {db_name} removed")


def create_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS complaints(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id TEXT UNIQUE,
        user_id INTEGER,
        name TEXT NOT NULL,
        mobile TEXT,
        ward TEXT,
        location TEXT NOT NULL,
        waste_type TEXT NOT NULL,
        complaint TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        priority TEXT DEFAULT 'Medium',
        remarks TEXT,
        assigned_driver TEXT,
        assigned_ward_officer TEXT,
        assigned_staff TEXT,
        image_path TEXT,
        gps_latitude REAL,
        gps_longitude REAL,
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

    print("Complaint Database Ready")


def migrate_old_complaints_schema():
    """Migrate legacy complaints schema to the current schema."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(complaints)")
    columns = [row[1] for row in cursor.fetchall()]

    if not columns:
        conn.close()
        return

    try:
        if 'citizen_name' in columns and 'name' not in columns:
            cursor.execute("ALTER TABLE complaints RENAME COLUMN citizen_name TO name")
            print("Migrated complaints.citizen_name to complaints.name")
    except sqlite3.OperationalError:
        pass

    try:
        if 'status' not in columns:
            cursor.execute("ALTER TABLE complaints ADD COLUMN status TEXT NOT NULL DEFAULT 'Pending'")
            print("Added missing complaints.status column")
    except sqlite3.OperationalError:
        pass

    try:
        if 'created_date' not in columns:
            cursor.execute("ALTER TABLE complaints ADD COLUMN created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            print("Added missing complaints.created_date column")
    except sqlite3.OperationalError:
        pass

    try:
        if 'user_id' not in columns:
            cursor.execute("ALTER TABLE complaints ADD COLUMN user_id INTEGER")
            print("Added missing complaints.user_id column")
    except sqlite3.OperationalError:
        pass

    try:
        if 'assigned_staff' not in columns:
            cursor.execute("ALTER TABLE complaints ADD COLUMN assigned_staff TEXT")
            print("Added missing complaints.assigned_staff column")
    except sqlite3.OperationalError:
        pass

    try:
        if 'image_path' not in columns:
            cursor.execute("ALTER TABLE complaints ADD COLUMN image_path TEXT")
            print("Added missing complaints.image_path column")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def create_ward_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS wards")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wards(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ward_name TEXT,
        area TEXT,
        email TEXT,
        address TEXT,
        supervisor TEXT,
        population INTEGER DEFAULT 0,
        waste_generation_kg REAL DEFAULT 0,
        vehicle_assignment TEXT,
        complaint_count INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()

    print("Ward Database Ready")


def create_vehicle_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_number TEXT UNIQUE NOT NULL,
        vehicle_type TEXT NOT NULL,
        capacity INTEGER,
        driver_name TEXT,
        status TEXT DEFAULT 'Active',
        ward_assigned TEXT,
        route TEXT,
        last_location TEXT,
        daily_collection_kg REAL DEFAULT 0,
        history TEXT DEFAULT ''
    )
    """)

    conn.commit()
    conn.close()

    print("Vehicle Database Ready")


def create_waste_collection_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS waste_collection(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER,
        ward TEXT,
        collection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        waste_quantity REAL,
        waste_type TEXT,
        status TEXT DEFAULT 'Completed',
        FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS households(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        house_id TEXT UNIQUE,
        citizen_name TEXT,
        mobile TEXT,
        address TEXT,
        ward TEXT,
        family_members INTEGER DEFAULT 1,
        gps TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

    print("Waste Collection Database Ready")


def create_tracking_database():
    """Create complaint tracking and assignment tables"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS complaint_tracking(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER,
        user_id INTEGER,
        action TEXT,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(complaint_id) REFERENCES complaints(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS work_assignments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER,
        assigned_to INTEGER,
        assigned_by INTEGER,
        assignment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        target_completion TIMESTAMP,
        actual_completion TIMESTAMP,
        status TEXT DEFAULT 'pending',
        notes TEXT,
        FOREIGN KEY(complaint_id) REFERENCES complaints(id),
        FOREIGN KEY(assigned_to) REFERENCES users(id),
        FOREIGN KEY(assigned_by) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER,
        recipient TEXT,
        channel TEXT,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        delivered INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()
    print("Tracking Database Ready")


def create_citizen_dashboard_tables():
    """Create citizen-specific dashboard tables"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS citizens(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        address TEXT,
        ward TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    
    # Citizen waste history
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS citizen_waste_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        collection_date TIMESTAMP,
        waste_quantity REAL,
        waste_type TEXT,
        location TEXT,
        collection_method TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    
    # Carbon credits earned
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS carbon_credits(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        waste_collection_id INTEGER,
        co2_saved_kg REAL,
        credits_earned REAL,
        credit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        redemption_status TEXT DEFAULT 'available',
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    
    # ESG scores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS esg_scores(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ward_id INTEGER,
        environmental_score REAL,
        social_score REAL,
        governance_score REAL,
        esg_score REAL,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(ward_id) REFERENCES wards(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS complaint_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER,
        status TEXT,
        remarks TEXT,
        changed_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(complaint_id) REFERENCES complaints(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS staff(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        name TEXT,
        role TEXT,
        ward TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS drivers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        name TEXT,
        vehicle_number TEXT,
        ward TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assignments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER,
        ward_officer_id INTEGER,
        driver_id INTEGER,
        staff_id INTEGER,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'assigned',
        FOREIGN KEY(complaint_id) REFERENCES complaints(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()
    print("Citizen Dashboard Database Ready")


def create_audit_log_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id {_id_column_definition()},
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        target_type TEXT,
        target_id INTEGER,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()


def log_audit_event(actor: str, action: str, target_type: Optional[str] = None,
                    target_id: Optional[int] = None, details: Optional[str] = None) -> bool:
    try:
        create_audit_log_table()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO audit_logs (actor, action, target_type, target_id, details) VALUES (?, ?, ?, ?, ?)",
            (actor, action, target_type, target_id, details or "")
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def create_backup_copy() -> Tuple[bool, str]:
    backup_dir = BASE_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    db_name = get_database_name()
    if not os.path.exists(db_name):
        return False, ""

    backup_path = backup_dir / f"{Path(db_name).stem}_{os.getpid()}_backup.bak"
    shutil.copy2(db_name, backup_path)
    return True, str(backup_path)


def restore_latest_backup() -> bool:
    backup_dir = BASE_DIR / "backups"
    if not backup_dir.exists():
        return False

    backup_files = sorted(backup_dir.glob("*.bak"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not backup_files:
        return False

    target_db = get_database_name()
    shutil.copy2(backup_files[0], target_db)
    return os.path.exists(target_db)


def initialize_all_databases():
    """Initialize all database tables"""
    create_database()
    create_ward_database()
    create_vehicle_database()
    create_waste_collection_database()
    migrate_old_complaints_schema()
    create_tracking_database()
    create_citizen_dashboard_tables()
    create_audit_log_table()
    print("All databases initialized successfully!")
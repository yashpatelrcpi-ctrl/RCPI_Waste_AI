import sqlite3
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

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


def get_connection():
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
        name TEXT NOT NULL,
        mobile TEXT,
        ward TEXT,
        location TEXT NOT NULL,
        waste_type TEXT NOT NULL,
        complaint TEXT NOT NULL,
        status TEXT NOT NULL,
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

    print("Complaint Database Ready")


def migrate_old_complaints_schema():
    """Migrate legacy complaints schema to the current schema.

    Older database files used a `citizen_name` field and may be missing
    `status` and `created_date`. This performs safe schema migration if the
    table already exists.
    """
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

    conn.commit()
    conn.close()


def create_ward_database():
    conn = get_connection()
    cursor = conn.cursor()

    # Drop old table if it exists to recreate with new schema
    cursor.execute("DROP TABLE IF EXISTS wards")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wards(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ward_name TEXT,
        area TEXT,
        email TEXT,
        address TEXT
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
        ward_assigned TEXT
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

    conn.commit()
    conn.close()

    print("Waste Collection Database Ready")


def create_tracking_database():
    """Create complaint tracking and assignment tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Complaint tracking
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
    
    # Work assignments
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
    
    conn.commit()
    conn.close()
    print("Tracking Database Ready")


def create_citizen_dashboard_tables():
    """Create citizen-specific dashboard tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
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
    
    conn.commit()
    conn.close()
    print("Citizen Dashboard Database Ready")


def initialize_all_databases():
    """Initialize all database tables"""
    create_database()
    create_ward_database()
    create_vehicle_database()
    create_waste_collection_database()
    migrate_old_complaints_schema()
    create_tracking_database()
    create_citizen_dashboard_tables()
    print("All databases initialized successfully!")
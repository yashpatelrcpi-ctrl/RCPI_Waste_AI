"""
Authentication Module for RCPI Waste AI System
Handles user authentication, role management, and sessions
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from database import get_connection

# Hash password with salt
def hash_password(password: str) -> str:
    """Hash password with salt"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${pwd_hash.hex()}"

def verify_password(password: str, hash_pwd: str) -> bool:
    """Verify password against hash"""
    try:
        salt, pwd_hash = hash_pwd.split('$')
        test_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return test_hash.hex() == pwd_hash
    except:
        return False

def create_session_token() -> str:
    """Generate secure session token"""
    return secrets.token_urlsafe(32)

class AuthManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path

    def _get_connection(self):
        if self.db_path:
            return sqlite3.connect(self.db_path, timeout=30, detect_types=sqlite3.PARSE_DECLTYPES)
        return get_connection()

    def create_auth_tables(self):
        """Create authentication tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'citizen',
                    full_name TEXT,
                    phone TEXT,
                    ward_id INTEGER,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    FOREIGN KEY(ward_id) REFERENCES wards(id)
                )
            ''')

            # Sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')

            # Roles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    permissions TEXT
                )
            ''')

            # Activity log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')

            conn.commit()
    
    def register_user(self, username: str, email: str, password: str, 
                     full_name: str, phone: str, role: str = 'citizen') -> Tuple[bool, str]:
        """Register new user"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                password_hash = hash_password(password)
                
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, role, full_name, phone)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (username, email, password_hash, role, full_name, phone))
                
                conn.commit()
                
                return True, "User registered successfully"
        except sqlite3.IntegrityError as e:
            if 'username' in str(e):
                return False, "Username already exists"
            elif 'email' in str(e):
                return False, "Email already exists"
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[str], Optional[dict]]:
        """Authenticate user and return session token"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Allow login by username or email
                cursor.execute('''
                    SELECT id, password_hash, role, is_active FROM users 
                    WHERE username = ? OR email = ?
                ''', (username, username))
                
                result = cursor.fetchone()
                
                if not result:
                    return False, None, None
                
                user_id, pwd_hash, role, is_active = result
                
                if not is_active:
                    return False, None, None
                
                if not verify_password(password, pwd_hash):
                    return False, None, None
                
                # Create session
                token = create_session_token()
                expires_at = datetime.now() + timedelta(days=7)
                
                cursor.execute('''
                    INSERT INTO sessions (user_id, token, expires_at)
                    VALUES (?, ?, ?)
                ''', (user_id, token, expires_at))
                
                # Update last login
                cursor.execute('''
                    UPDATE users SET last_login = ? WHERE id = ?
                ''', (datetime.now(), user_id))
                
                # Log activity
                cursor.execute('''
                    INSERT INTO activity_log (user_id, action, details)
                    VALUES (?, ?, ?)
                ''', (user_id, 'LOGIN', 'User logged in'))
                
                conn.commit()
                
                user_data = {
                    'user_id': user_id,
                    'username': username,
                    'role': role
                }
                
                return True, token, user_data
        
        except Exception as e:
            return False, None, None
    
    def get_all_users(self, role: str = None):
        """Return all users or users filtered by role."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if role:
                    cursor.execute('SELECT id, username, email, role, full_name, phone, is_active, created_at FROM users WHERE role = ? ORDER BY created_at DESC', (role,))
                else:
                    cursor.execute('SELECT id, username, email, role, full_name, phone, is_active, created_at FROM users ORDER BY created_at DESC')
                rows = cursor.fetchall()
                return [
                {
                    'id': row[0],
                    'username': row[1],
                    'email': row[2],
                    'role': row[3],
                    'full_name': row[4],
                    'phone': row[5],
                    'is_active': bool(row[6]),
                    'created_at': row[7]
                }
                for row in rows
            ]
        except Exception:
            return []

    def set_user_active_status(self, user_id: int, is_active: bool) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET is_active = ? WHERE id = ?', (1 if is_active else 0, user_id))
                conn.commit()
                return True
        except Exception:
            return False

    def delete_user(self, user_id: int) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                conn.commit()
                return True
        except Exception:
            return False
    
    def verify_session(self, token: str) -> Tuple[bool, Optional[dict]]:
        """Verify session token"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT u.id, u.username, u.role, u.is_active, s.expires_at
                    FROM sessions s
                    JOIN users u ON s.user_id = u.id
                    WHERE s.token = ? AND s.is_active = 1
                ''', (token,))
                
                result = cursor.fetchone()
            
            if not result:
                return False, None
            
            user_id, username, role, is_active, expires_at = result
            # Safely parse expires_at which may be stored as text or timestamp
            try:
                if isinstance(expires_at, str):
                    exp_dt = datetime.fromisoformat(expires_at)
                else:
                    exp_dt = expires_at
            except Exception:
                exp_dt = None

            if not is_active or (exp_dt and exp_dt < datetime.now()):
                return False, None
            
            return True, {
                'user_id': user_id,
                'username': username,
                'role': role
            }
        
        except Exception as e:
            return False, None
    
    def logout_user(self, token: str) -> bool:
        """Logout user by invalidating session"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE sessions SET is_active = 0 WHERE token = ?
                ''', (token,))
                
                conn.commit()
                return True
        except:
            return False
    
    def log_activity(self, user_id: int, action: str, details: str = ""):
        """Log user activity"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO activity_log (user_id, action, details)
                    VALUES (?, ?, ?)
                ''', (user_id, action, details))
                
                conn.commit()
        except:
            pass

# Initialize auth
auth_manager = AuthManager()
auth_manager.create_auth_tables()

# Seed demo users if not present
def seed_demo_users():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            if not cursor.fetchone():
                auth_manager.register_user('admin', 'admin@example.com', 'admin@123', 'Administrator', '0000000000', role='admin')
            cursor.execute("SELECT id FROM users WHERE username = 'test_citizen'")
            if not cursor.fetchone():
                auth_manager.register_user('test_citizen', 'citizen@example.com', 'citizen@123', 'Test Citizen', '0000000000', role='citizen')
            cursor.execute("SELECT id FROM users WHERE username = 'supervisor'")
            if not cursor.fetchone():
                auth_manager.register_user('supervisor', 'supervisor@example.com', 'supervisor@123', 'Supervisor User', '0000000000', role='supervisor')
            cursor.execute("SELECT id FROM users WHERE username = 'driver1'")
            if not cursor.fetchone():
                auth_manager.register_user('driver1', 'driver1@example.com', 'driver@123', 'Driver One', '0000000000', role='driver')
            cursor.execute("SELECT id FROM users WHERE username = 'staff1'")
            if not cursor.fetchone():
                auth_manager.register_user('staff1', 'staff1@example.com', 'staff@123', 'Staff One', '0000000000', role='staff')
    except Exception:
        pass

seed_demo_users()

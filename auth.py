"""
Authentication Module for RCPI Waste AI System
Handles user authentication, role management, and sessions
"""

import sqlite3
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple
from database import get_connection, initialize_all_databases
from notifications import NotificationManager

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

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS citizens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    citizen_id TEXT,
                    address TEXT,
                    ward TEXT,
                    house_id TEXT,
                    gps_location TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')

            # Compatibility upgrade for older database files that may lack
            # the expanded citizen profile columns used by registration and login.
            cursor.execute("PRAGMA table_info(citizens)")
            citizen_columns = {row[1] for row in cursor.fetchall()}
            if 'citizen_id' not in citizen_columns or 'address' not in citizen_columns or 'ward' not in citizen_columns or 'house_id' not in citizen_columns or 'gps_location' not in citizen_columns or 'created_at' not in citizen_columns:
                cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="citizens"')
                if cursor.fetchone():
                    cursor.execute('ALTER TABLE citizens RENAME TO citizens_old')
                    cursor.execute('''
                        CREATE TABLE citizens (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER UNIQUE NOT NULL,
                            citizen_id TEXT,
                            address TEXT,
                            ward TEXT,
                            house_id TEXT,
                            gps_location TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(user_id) REFERENCES users(id)
                        )
                    ''')
                    cursor.execute("PRAGMA table_info(citizens_old)")
                    old_columns = {row[1] for row in cursor.fetchall()}
                    select_parts = ['id', 'user_id']
                    if 'citizen_id' in old_columns:
                        select_parts.append('citizen_id')
                    else:
                        select_parts.append("'RCPI-CIT-' || printf('%05d', user_id) AS citizen_id")
                    if 'address' in old_columns:
                        select_parts.append('address')
                    else:
                        select_parts.append("'' AS address")
                    if 'ward' in old_columns:
                        select_parts.append('ward')
                    else:
                        select_parts.append("'' AS ward")
                    if 'house_id' in old_columns:
                        select_parts.append('house_id')
                    else:
                        select_parts.append("'' AS house_id")
                    if 'gps_location' in old_columns:
                        select_parts.append('gps_location')
                    else:
                        select_parts.append("'' AS gps_location")
                    if 'created_at' in old_columns:
                        select_parts.append('created_at')
                    else:
                        select_parts.append("CURRENT_TIMESTAMP AS created_at")
                    cursor.execute(
                        f"""
                        INSERT INTO citizens (id, user_id, citizen_id, address, ward, house_id, gps_location, created_at)
                        SELECT {', '.join(select_parts)}
                        FROM citizens_old
                        """
                    )
                    cursor.execute('DROP TABLE citizens_old')

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

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_used INTEGER DEFAULT 0,
                    used_at TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS otp_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT NOT NULL,
                    token TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    verified INTEGER DEFAULT 0
                )
            ''')

            conn.commit()
    
    def register_user(self, username: str, email: str, password: str, 
                     full_name: str, phone: str, role: str = 'citizen',
                     address: str = None, ward: str = None,
                     house_id: str = None, gps_location: str = None) -> Tuple[bool, str]:
        """Register new user and create a citizen profile when needed."""
        try:
            initialize_all_databases()
            self.create_auth_tables()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                password_hash = hash_password(password)

                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, role, full_name, phone)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (username, email, password_hash, role, full_name, phone))

                user_id = cursor.lastrowid
                citizen_id = None
                if role == 'citizen':
                    citizen_id = f"RCPI-CIT-{user_id:05d}"
                    cursor.execute('''
                        INSERT INTO citizens (user_id, citizen_id, address, ward, house_id, gps_location)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (user_id, citizen_id, address or '', ward or '', house_id or '', gps_location or ''))
                elif role == 'staff':
                    cursor.execute('''
                        INSERT INTO staff (user_id, name, role, ward)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, full_name or username, 'staff', ward or ''))
                elif role == 'driver':
                    cursor.execute('''
                        INSERT INTO drivers (user_id, name, vehicle_number, ward)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, full_name or username, '', ward or ''))

                conn.commit()
                self.log_activity(user_id, 'REGISTER', f'Registered {role} account')

                if role == 'citizen' and citizen_id:
                    try:
                        from notifications import NotificationManager
                        subject = 'Welcome to RCPI Waste AI'
                        body = (
                            f"Hello {full_name or username}, your citizen account is ready. "
                            f"Citizen ID: {citizen_id} | Login ID: {username} | Password: {password}"
                        )
                        NotificationManager.send_email(user_id, email, subject, body)
                        if phone:
                            NotificationManager.send_sms(user_id, phone, f"RCPI Waste AI: Citizen ID {citizen_id}; Login ID {username}; Password {password}")
                            NotificationManager.send_whatsapp(user_id, phone, f"RCPI Waste AI: Citizen ID {citizen_id}; Login ID {username}; Password {password}")
                    except Exception:
                        pass

                return True, f"User registered successfully{' - Citizen ID ' + citizen_id if citizen_id else ''}"
        except sqlite3.IntegrityError as e:
            if 'username' in str(e):
                return False, "Username already exists"
            elif 'email' in str(e):
                return False, "Email already exists"
            return False, str(e)
        except Exception as e:
            return False, str(e)

    def get_user_by_identifier(self, identifier: str) -> Optional[dict]:
        """Lookup a user by username, email, phone, or citizen id."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.id, u.username, u.email, u.phone, u.full_name, u.role, c.citizen_id
                    FROM users u
                    LEFT JOIN citizens c ON c.user_id = u.id
                    WHERE u.username = ? OR u.email = ? OR u.phone = ? OR c.citizen_id = ?
                ''', (identifier, identifier, identifier, identifier))
                row = cursor.fetchone()
                if not row:
                    return None
                return {
                    'id': row[0],
                    'username': row[1],
                    'email': row[2],
                    'phone': row[3],
                    'full_name': row[4],
                    'role': row[5],
                    'citizen_id': row[6],
                }
        except Exception:
            return None

    def create_password_reset_token(self, user_id: int) -> Tuple[bool, Optional[dict]]:
        """Create a password reset token and return it with contact details."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT email, phone FROM users WHERE id = ?', (user_id,))
                row = cursor.fetchone()
                if not row:
                    return False, None
                email, phone = row
                token = secrets.token_hex(3).upper()
                cursor.execute('DELETE FROM password_reset_tokens WHERE user_id = ?', (user_id,))
                cursor.execute('''
                    INSERT INTO password_reset_tokens (user_id, token, expires_at)
                    VALUES (?, ?, ?)
                ''', (user_id, token, datetime.now() + timedelta(minutes=15)))
                conn.commit()

                try:
                    if phone:
                        NotificationManager.send_sms(user_id, phone, f"Your RCPI password reset code is {token}. Use it within 15 minutes.")
                    if email:
                        NotificationManager.send_email(user_id, email, 'RCPI Password Reset Code', f'Your password reset code is {token}.')
                except Exception:
                    pass

                return True, {'token': token, 'email': email, 'phone': phone}
        except Exception:
            return False, None

    def _generate_otp(self, digits: int = 6) -> str:
        return ''.join(str(secrets.randbelow(10)) for _ in range(digits))

    def _store_otp(self, phone: str, purpose: str, data: Optional[dict] = None) -> Optional[dict]:
        try:
            token = self._generate_otp()
            expires_at = datetime.now() + timedelta(minutes=15)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO otp_tokens (phone, token, purpose, data, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (phone, token, purpose, json.dumps(data) if data else None, expires_at))
                otp_id = cursor.lastrowid
                conn.commit()
            return {'id': otp_id, 'token': token, 'phone': phone, 'expires_at': expires_at}
        except Exception:
            return None

    def create_registration_otp(self, username: str, email: str, password: str, full_name: str, phone: str, address: str = None, ward: str = None, house_id: str = None, gps_location: str = None) -> Tuple[bool, Optional[dict]]:
        try:
            existing_user = self.get_user_by_identifier(username) or self.get_user_by_identifier(email) or self.get_user_by_identifier(phone)
            if existing_user:
                return False, {'error': 'A user with the same username, email, or phone already exists.'}

            payload = {
                'username': username,
                'email': email,
                'password': password,
                'full_name': full_name,
                'phone': phone,
                'address': address or '',
                'ward': ward or '',
                'house_id': house_id or '',
                'gps_location': gps_location or '',
            }
            otp_metadata = self._store_otp(phone, 'registration', payload)
            if not otp_metadata:
                return False, {'error': 'Unable to generate OTP at this time.'}

            try:
                NotificationManager.send_sms(0, phone, f"Your RCPI registration OTP is {otp_metadata['token']}. Use it within 15 minutes.")
            except Exception:
                pass

            return True, {'otp_id': otp_metadata['id'], 'token': otp_metadata['token'], 'phone': phone}
        except Exception:
            return False, {'error': 'Failed to initiate registration OTP.'}

    def verify_registration_otp(self, otp_id: int, token: str) -> Tuple[bool, str, Optional[str], Optional[dict]]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, token, data, expires_at, verified
                    FROM otp_tokens
                    WHERE id = ? AND purpose = 'registration'
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (otp_id,))
                row = cursor.fetchone()
                if not row:
                    return False, 'OTP record not found.', None, None
                stored_id, stored_token, data, expires_at, verified = row
                if verified:
                    return False, 'OTP has already been used.', None, None
                if stored_token != token:
                    return False, 'Invalid OTP code.', None, None
                try:
                    expires_dt = expires_at if not isinstance(expires_at, str) else datetime.fromisoformat(expires_at)
                except Exception:
                    expires_dt = None
                if expires_dt and expires_dt < datetime.now():
                    return False, 'OTP has expired.', None, None

                payload = json.loads(data or '{}')
                success, message = self.register_user(
                    payload.get('username'),
                    payload.get('email'),
                    payload.get('password'),
                    payload.get('full_name'),
                    payload.get('phone'),
                    role='citizen',
                    address=payload.get('address'),
                    ward=payload.get('ward'),
                    house_id=payload.get('house_id'),
                    gps_location=payload.get('gps_location')
                )
                if not success:
                    return False, message, None, None

                cursor.execute('UPDATE otp_tokens SET verified = 1 WHERE id = ?', (stored_id,))
                conn.commit()

            ok, auth_token, user = self.authenticate_user(payload.get('username'), payload.get('password'))
            if not ok:
                return False, 'Registration completed, but automatic login failed.', None, None

            return True, 'Registration verified successfully.', auth_token, user
        except Exception:
            return False, 'Unable to verify registration OTP.', None, None

    def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """Reset a user password using a valid reset token."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, expires_at, is_used
                    FROM password_reset_tokens
                    WHERE token = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (token,))
                row = cursor.fetchone()
                if not row:
                    return False
                user_id, expires_at, is_used = row
                if is_used:
                    return False
                try:
                    expires_dt = expires_at if not isinstance(expires_at, str) else datetime.fromisoformat(expires_at)
                except Exception:
                    expires_dt = None
                if expires_dt and expires_dt < datetime.now():
                    return False
                password_hash = hash_password(new_password)
                cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
                cursor.execute('UPDATE password_reset_tokens SET is_used = 1, used_at = ? WHERE token = ?', (datetime.now(), token))
                conn.commit()
                self.log_activity(user_id, 'PASSWORD_RESET', 'Password reset via token')
                return True
        except Exception:
            return False
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[str], Optional[dict]]:
        """Authenticate user and return session token."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT u.id, u.username, u.email, u.phone, u.password_hash, u.role, u.is_active
                    FROM users u
                    LEFT JOIN citizens c ON c.user_id = u.id
                    WHERE u.username = ? OR u.email = ? OR u.phone = ? OR c.citizen_id = ?
                ''', (username, username, username, username))

                result = cursor.fetchone()

                if not result:
                    return False, None, None

                user_id, db_username, email, phone, pwd_hash, role, is_active = result

                if not is_active:
                    return False, None, None

                if not verify_password(password, pwd_hash):
                    return False, None, None

                token = create_session_token()
                expires_at = datetime.now() + timedelta(days=7)

                cursor.execute('''
                    INSERT INTO sessions (user_id, token, expires_at)
                    VALUES (?, ?, ?)
                ''', (user_id, token, expires_at))

                cursor.execute('''
                    UPDATE users SET last_login = ? WHERE id = ?
                ''', (datetime.now(), user_id))

                cursor.execute('''
                    INSERT INTO activity_log (user_id, action, details)
                    VALUES (?, ?, ?)
                ''', (user_id, 'LOGIN', 'User logged in'))

                conn.commit()

                user_data = {
                    'user_id': user_id,
                    'username': db_username,
                    'email': email,
                    'phone': phone,
                    'role': role,
                }

                if role == 'citizen':
                    cursor.execute('SELECT citizen_id, address, ward, house_id, gps_location FROM citizens WHERE user_id = ?', (user_id,))
                    citizen_row = cursor.fetchone()
                    if citizen_row:
                        user_data['citizen_id'] = citizen_row[0]
                        user_data['address'] = citizen_row[1]
                        user_data['ward'] = citizen_row[2]
                        user_data['house_id'] = citizen_row[3]
                        user_data['gps_location'] = citizen_row[4]

                return True, token, user_data

        except Exception:
            return False, None, None
    
    def get_all_users(self, role: str = None, search: str = None):
        """Return all users or users filtered by role and search text."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = '''
                    SELECT u.id, u.username, u.email, u.role, u.full_name, u.phone, u.is_active, u.created_at,
                           c.citizen_id, c.address, c.ward, c.house_id, c.gps_location
                    FROM users u
                    LEFT JOIN citizens c ON c.user_id = u.id
                '''
                params = []
                conditions = []
                if role:
                    conditions.append('u.role = ?')
                    params.append(role)
                if search:
                    conditions.append('(u.username LIKE ? OR u.email LIKE ? OR u.phone LIKE ? OR c.citizen_id LIKE ? OR c.ward LIKE ? OR c.house_id LIKE ?)')
                    search_value = f'%{search}%'
                    params.extend([search_value, search_value, search_value, search_value, search_value, search_value])
                if conditions:
                    query += ' WHERE ' + ' AND '.join(conditions)
                query += ' ORDER BY u.created_at DESC'
                cursor.execute(query, params)
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
                        'created_at': row[7],
                        'citizen_id': row[8],
                        'address': row[9],
                        'ward': row[10],
                        'house_id': row[11],
                        'gps_location': row[12],
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

    def reset_user_password(self, user_id: int, new_password: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                password_hash = hash_password(new_password)
                cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
                conn.commit()
                self.log_activity(user_id, 'PASSWORD_RESET', 'Password reset by admin')
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
        initialize_all_databases()
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

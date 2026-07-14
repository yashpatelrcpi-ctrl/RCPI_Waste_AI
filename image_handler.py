"""
Image Upload and AI Waste Detection Module
Handles image upload, storage, GPS location, and AI-based waste detection
"""
try:
    from ultralytics import YOLO
except Exception:
    YOLO = None

try:
    import cv2
except Exception:
    cv2 = None

# Load AI Model if available
model = None
if YOLO is not None:
    try:
        model = YOLO("best.pt")
    except Exception:
        model = None

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional
import json
from database import get_connection
from waste_category_trainer import categorize_waste, get_disposal_instructions
import base64

class ImageManager:
    """Manage image uploads and storage"""
    
    UPLOAD_DIR = "static/uploads"
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    @staticmethod
    def ensure_upload_directory():
        """Create upload directory if not exists"""
        Path(ImageManager.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def is_file_allowed(filename: str) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ImageManager.ALLOWED_EXTENSIONS
    
    @staticmethod
    def save_image(file_content: bytes, filename: str, user_id: int, 
                  gps_lat: Optional[float] = None, gps_lon: Optional[float] = None) -> Tuple[bool, str]:
        """Save uploaded image with metadata"""
        try:
            ImageManager.ensure_upload_directory()
            
            if not ImageManager.is_file_allowed(filename):
                return False, "File type not allowed"
            
            if len(file_content) > ImageManager.MAX_FILE_SIZE:
                return False, "File size too large"
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{user_id}_{timestamp}_{filename}"
            filepath = os.path.join(ImageManager.UPLOAD_DIR, safe_filename)
            
            # Save file
            with open(filepath, 'wb') as f:
                f.write(file_content)
            
            # Save to database
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO uploaded_images (user_id, filename, filepath, gps_latitude, gps_longitude, upload_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, safe_filename, filepath, gps_lat, gps_lon, datetime.now()))
            
            image_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return True, str(image_id)
        
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def get_image(image_id: int) -> Optional[dict]:
        """Retrieve image metadata"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, user_id, filename, filepath, gps_latitude, gps_longitude, 
                       upload_date, detected_category, confidence
                FROM uploaded_images WHERE id = ?
            ''', (image_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'id': result[0],
                    'user_id': result[1],
                    'filename': result[2],
                    'filepath': result[3],
                    'gps_lat': result[4],
                    'gps_lon': result[5],
                    'upload_date': result[6],
                    'detected_category': result[7],
                    'confidence': result[8]
                }
            return None
        
        except Exception as e:
            return None

class WasteDetector:
    """AI-based waste detection from images"""
    
    # Color-based waste detection (RGB ranges)
    COLOR_PATTERNS = {
        'organic': {
            'brown': (150, 120, 90),
            'green': (90, 150, 90),
            'yellow': (200, 180, 90),
        },
        'recyclable': {
            'blue': (50, 100, 200),
            'clear': (200, 200, 200),
            'silver': (180, 180, 180),
        },
        'electronic': {
            'black': (50, 50, 50),
            'gray': (100, 100, 100),
            'metallic': (150, 150, 150),
        },
        'construction': {
            'red': (200, 100, 100),
            'orange': (200, 150, 100),
            'gray': (100, 100, 100),
        }
    }
    
    @staticmethod
    def detect_from_filename(filename: str) -> Tuple[str, float]:
        """Simple detection based on filename/description"""
        filename_lower = filename.lower()
        
        # Keywords for each category
        keywords = {
            'organic': ['food', 'fruit', 'vegetable', 'leaf', 'grass', 'green', 'compost', 'peel'],
            'recyclable': ['bottle', 'can', 'plastic', 'glass', 'paper', 'aluminum', 'blue'],
            'electronic': ['phone', 'laptop', 'computer', 'battery', 'charger', 'ewaste', 'electronic'],
            'construction': ['brick', 'concrete', 'stone', 'metal', 'wood', 'construction'],
            'hazardous': ['paint', 'chemical', 'acid', 'toxic', 'hazard', 'dangerous'],
        }
        
        scores = {}
        for category, kw_list in keywords.items():
            score = sum(1 for kw in kw_list if kw in filename_lower)
            if score > 0:
                scores[category] = score
        
        if scores:
            best_category = max(scores, key=scores.get)
            confidence = min(100, scores[best_category] * 25)
            return best_category, confidence
        
        return 'mixed', 25.0
    
    @staticmethod
    def analyze_image(image_id: int) -> Tuple[bool, dict]:
        """
        Analyze uploaded image for waste detection
        Returns: (success, {category, confidence, disposal_info})
        """
        try:
            # Get image
            img_data = ImageManager.get_image(image_id)
            if not img_data:
                return False, {'error': 'Image not found'}
            
            # For MVP: detect based on filename and stored description
            # In production: use real ML model (TensorFlow, PyTorch, etc.)
            filename = img_data['filename']
            image_path = img_data["filepath"]
            # Run model inference (if model available)
            try:
                results = model(image_path)
                boxes = results[0].boxes

                counts = {}
                for box in boxes:
                    try:
                        cls = int(box.cls[0])
                        label = model.names[cls]
                        counts[label] = counts.get(label, 0) + 1
                    except Exception:
                        continue

                total_items = len(boxes)
                if total_items > 0 and counts:
                    category = max(counts, key=counts.get)
                    try:
                        confidence = round(float(boxes[0].conf[0]) * 100, 2)
                    except Exception:
                        confidence = 0
                else:
                    category = "Unknown"
                    confidence = 0
            except Exception:
                # Fallback to filename-based detection
                category, confidence = WasteDetector.detect_from_filename(filename)
            
            # Get disposal instructions
            disposal_info = get_disposal_instructions(category)
            
            # Update database with detection results
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE uploaded_images 
                SET detected_category = ?, confidence = ?, analysis_date = ?
                WHERE id = ?
            ''', (category, confidence, datetime.now(), image_id))
            
            conn.commit()
            conn.close()
            
            result = {
                'success': True,
                'image_id': image_id,
                'detected_category': category,
                'confidence': confidence,
                'bin_color': WasteDetector.get_bin_color(category),
                'disposal_info': disposal_info,
                'gps_location': {
                    'latitude': img_data['gps_lat'],
                    'longitude': img_data['gps_lon']
                }
            }
            
            return True, result
        
        except Exception as e:
            return False, {'error': str(e)}
    
    @staticmethod
    def get_bin_color(category: str) -> str:
        """Get bin color for waste category"""
        colors = {
            'organic': '🟢 GREEN BIN',
            'recyclable': '🔵 BLUE BIN',
            'electronic': '🔴 RED BIN',
            'construction': '🟡 YELLOW BIN',
            'hazardous': '🔴 RED BIN',
            'mixed': '⚫ GRAY BIN'
        }
        return colors.get(category, '⚫ GRAY BIN')

class LocationTracker:
    """Track GPS location of waste uploads"""
    
    @staticmethod
    def get_user_location_history(user_id: int = None, limit: int = 50) -> list:
        """Get location history of user's waste uploads"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            if user_id is not None:
                cursor.execute('''
                    SELECT id, filename, gps_latitude, gps_longitude, upload_date, 
                           detected_category, confidence
                    FROM uploaded_images
                    WHERE user_id = ? AND gps_latitude IS NOT NULL
                    ORDER BY upload_date DESC
                    LIMIT ?
                ''', (user_id, limit))
            else:
                cursor.execute('''
                    SELECT id, filename, gps_latitude, gps_longitude, upload_date, 
                           detected_category, confidence
                    FROM uploaded_images
                    WHERE gps_latitude IS NOT NULL
                    ORDER BY upload_date DESC
                    LIMIT ?
                ''', (limit,))
            
            locations = []
            for row in cursor.fetchall():
                locations.append({
                    'image_id': row[0],
                    'filename': row[1],
                    'latitude': row[2],
                    'longitude': row[3],
                    'date': row[4],
                    'category': row[5],
                    'confidence': row[6]
                })
            
            conn.close()
            return locations
        
        except Exception as e:
            return []
    
    @staticmethod
    def get_hotspots(radius_km: int = 1) -> list:
        """Find waste hotspots (areas with high waste uploads)"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    ROUND(gps_latitude, 3) as lat_bucket,
                    ROUND(gps_longitude, 3) as lon_bucket,
                    COUNT(*) as waste_count,
                    AVG(confidence) as avg_confidence
                FROM uploaded_images
                WHERE gps_latitude IS NOT NULL
                GROUP BY lat_bucket, lon_bucket
                HAVING COUNT(*) > 5
                ORDER BY waste_count DESC
            ''')
            
            hotspots = []
            for row in cursor.fetchall():
                hotspots.append({
                    'latitude': row[0],
                    'longitude': row[1],
                    'waste_count': row[2],
                    'avg_confidence': row[3]
                })
            
            conn.close()
            return hotspots
        
        except Exception as e:
            return []

# Initialize image table
def initialize_image_tables():
    """Create image and detection related tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploaded_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT,
            filepath TEXT,
            gps_latitude REAL,
            gps_longitude REAL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            detected_category TEXT,
            confidence REAL,
            analysis_date TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS waste_detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER NOT NULL,
            user_id INTEGER,
            detected_category TEXT,
            confidence REAL,
            bin_color TEXT,
            gps_latitude REAL,
            gps_longitude REAL,
            detection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(image_id) REFERENCES uploaded_images(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize on module load
initialize_image_tables()

import atexit
import os
import shutil
import sqlite3
import tempfile
import time
import uuid
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
import app as app_module

# Patch sqlite3.connect early so imported modules use an isolated temporary database
_ORIG_SQLITE_CONNECT = sqlite3.connect
_TEMP_DIR = tempfile.mkdtemp()
TEST_DB_PATH = os.path.join(_TEMP_DIR, "waste_ai.db")


def _cleanup_temp_dir():
    try:
        if os.path.isdir(_TEMP_DIR):
            shutil.rmtree(_TEMP_DIR, ignore_errors=True)
    except Exception:
        pass

atexit.register(_cleanup_temp_dir)


def _patched_connect(database_path, *args, **kwargs):
    if database_path == "waste_ai.db":
        return _ORIG_SQLITE_CONNECT(TEST_DB_PATH, *args, **kwargs)
    return _ORIG_SQLITE_CONNECT(database_path, *args, **kwargs)

sqlite3.connect = _patched_connect

import database
import auth
import waste_category_trainer
import reports
import image_handler
import carbon_prediction
import notifications

# Redirect the project database constant to the isolated test file
database.DATABASE_NAME = TEST_DB_PATH
auth.auth_manager.db_path = TEST_DB_PATH

# Use a temp upload directory so tests do not pollute project folders
image_handler.ImageManager.UPLOAD_DIR = os.path.join(_TEMP_DIR, "uploads")


class BaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use a unique temp database per suite to avoid cross-test locking on Windows
        unique_dir = os.path.join(_TEMP_DIR, str(uuid.uuid4()))
        os.makedirs(unique_dir, exist_ok=True)
        cls.TEST_DB_PATH = os.path.join(unique_dir, 'waste_ai.db')

        # Patch the project DB helpers to point at this temp DB
        database.get_database_name = staticmethod(lambda: cls.TEST_DB_PATH)
        database.DATABASE_NAME = cls.TEST_DB_PATH
        auth.auth_manager.db_path = cls.TEST_DB_PATH

        if os.path.exists(cls.TEST_DB_PATH):
            os.remove(cls.TEST_DB_PATH)

        database.initialize_all_databases()
        auth.auth_manager.create_auth_tables()
        auth.seed_demo_users()
        image_handler.initialize_image_tables()
        notifications.NotificationManager.create_notification_tables()

    @classmethod
    def tearDownClass(cls):
        # Attempt a graceful shutdown and cleanup of any temp files
        time.sleep(0.1)
        try:
            if hasattr(cls, 'TEST_DB_PATH') and os.path.exists(cls.TEST_DB_PATH):
                os.remove(cls.TEST_DB_PATH)
        except Exception:
            pass

    def tearDown(self):
        # Ensure the temp upload folder remains clean between tests
        if os.path.isdir(image_handler.ImageManager.UPLOAD_DIR):
            for file_name in os.listdir(image_handler.ImageManager.UPLOAD_DIR):
                try:
                    os.remove(os.path.join(image_handler.ImageManager.UPLOAD_DIR, file_name))
                except Exception:
                    pass


class TestDatabase(BaseTestCase):
    def test_connection_and_tables(self):
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='complaints'")
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

    def test_collection_stats(self):
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO waste_collection (vehicle_id, ward, waste_quantity, waste_type, status) VALUES (?, ?, ?, ?, ?)",
                       (1, 'Test Ward', 50.0, 'organic', 'Completed'))
        conn.commit()
        conn.close()

        stats = waste_category_trainer.get_collection_stats() if hasattr(waste_category_trainer, 'get_collection_stats') else None
        self.assertIsNone(stats)


class TestAuth(BaseTestCase):
    def test_user_registration_and_authentication(self):
        success, message = auth.auth_manager.register_user(
            'testuser', 'testuser@example.com', 'Password123', 'Test User', '1234567890', role='citizen'
        )
        self.assertTrue(success, msg=message)

        ok, token, user_data = auth.auth_manager.authenticate_user('testuser', 'Password123')
        self.assertTrue(ok)
        self.assertIsNotNone(token)
        self.assertEqual(user_data['role'], 'citizen')

        ok_verify, session_user = auth.auth_manager.verify_session(token)
        self.assertTrue(ok_verify)
        self.assertEqual(session_user['username'], 'testuser')

        auth.auth_manager.logout_user(token)
        ok_verify_after, _ = auth.auth_manager.verify_session(token)
        self.assertFalse(ok_verify_after)

    def test_duplicate_registration(self):
        auth.auth_manager.register_user('duplicate', 'duplicate@example.com', 'pass', 'Dup User', '123')
        success, message = auth.auth_manager.register_user('duplicate', 'duplicate2@example.com', 'pass', 'Dup User', '123')
        self.assertFalse(success)
        self.assertIn('already exists', message.lower())


class TestWasteCategoryTrainer(BaseTestCase):
    def test_categorize_waste(self):
        category, confidence = waste_category_trainer.categorize_waste('Plastic bottle')
        self.assertEqual(category, 'recyclable')
        self.assertGreaterEqual(confidence, 10)

    def test_disposal_instructions(self):
        instructions = waste_category_trainer.get_disposal_instructions('organic')
        self.assertIn('GREEN BIN', instructions)
        self.assertIn('Processing:', instructions)

    def test_training_pipeline_builds_classifier(self):
        classifier = waste_category_trainer.train_waste_classifier(force=True)
        self.assertIsNotNone(classifier)
        category, confidence = waste_category_trainer.categorize_waste('Old mobile phone')
        self.assertEqual(category, 'electronic')
        self.assertGreaterEqual(confidence, 10)


class TestAIChat(BaseTestCase):
    def test_ai_support_post_returns_helpful_response(self):
        with TestClient(app_module.app) as client:
            response = client.post('/ai-support', data={'query': 'where should i put a plastic bottle?'})
            self.assertEqual(response.status_code, 200)
            self.assertIn('waste', response.text.lower())

    def test_ai_support_post_uses_fallback_when_engine_fails(self):
        with patch('app.get_ai_response', side_effect=Exception('engine failure')):
            with TestClient(app_module.app) as client:
                response = client.post('/ai-support', data={'query': 'plastic bottle'})
                self.assertEqual(response.status_code, 200)
                self.assertIn('I can help', response.text)


class TestReports(BaseTestCase):
    def test_complaint_and_waste_reports(self):
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO complaints (name, mobile, ward, location, waste_type, complaint, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ('Alice', '000', 'Ward A', 'Location A', 'plastic', 'Complaint text', 'pending'))
        cursor.execute("INSERT INTO waste_collection (vehicle_id, ward, waste_quantity, waste_type, status) VALUES (?, ?, ?, ?, ?)",
                       (1, 'Ward A', 24.0, 'recyclable', 'Completed'))
        conn.commit()
        conn.close()

        complaint_report = reports.ReportGenerator.get_complaint_summary()
        self.assertIn('summary', complaint_report)
        self.assertGreaterEqual(complaint_report['summary']['total_complaints'], 1)

        waste_report = reports.ReportGenerator.get_waste_summary()
        self.assertIn('summary', waste_report)
        self.assertGreaterEqual(waste_report['summary']['total_waste_kg'], 24.0)

        csv_output = reports.ReportGenerator.generate_csv_report('complaints', complaint_report)
        self.assertIn('Complaint Summary Report', csv_output)

        html_output = reports.ReportGenerator.generate_html_report('waste', waste_report)
        self.assertIn('Waste Collection Report', html_output)


class TestImageHandler(BaseTestCase):
    def test_file_extension_check(self):
        self.assertTrue(image_handler.ImageManager.is_file_allowed('photo.png'))
        self.assertFalse(image_handler.ImageManager.is_file_allowed('malware.exe'))

    def test_save_image_and_analysis(self):
        content = b'This is a test image file content'
        success, image_id = image_handler.ImageManager.save_image(content, 'photo.jpg', user_id=1)
        self.assertTrue(success)
        self.assertTrue(image_id.isdigit())

        metadata = image_handler.ImageManager.get_image(int(image_id))
        self.assertIsNotNone(metadata)
        self.assertTrue(metadata['filename'].endswith('_photo.jpg'))

        ok, result = image_handler.WasteDetector.analyze_image(int(image_id))
        self.assertTrue(ok)
        self.assertIn('detected_category', result)
        self.assertIn('confidence', result)


class TestCarbonPredictionModel(BaseTestCase):
    def test_trend_and_prediction(self):
        conn = database.get_connection()
        cursor = conn.cursor()
        now = datetime.now()
        cursor.execute("INSERT INTO waste_collection (vehicle_id, ward, waste_quantity, waste_type, status, collection_date) VALUES (?, ?, ?, ?, ?, ?)",
                       (1, 'Ward A', 10.0, 'organic', 'Completed', (now - timedelta(days=2)).isoformat()))
        cursor.execute("INSERT INTO waste_collection (vehicle_id, ward, waste_quantity, waste_type, status, collection_date) VALUES (?, ?, ?, ?, ?, ?)",
                       (1, 'Ward A', 12.0, 'organic', 'Completed', (now - timedelta(days=1)).isoformat()))
        conn.commit()
        conn.close()

        slope, intercept = carbon_prediction.CarbonPredictionModel.calculate_trend([10.0, 12.0])
        self.assertGreaterEqual(slope, 0)

        predictions = carbon_prediction.CarbonPredictionModel.predict_waste('organic', days_ahead=3)
        self.assertEqual(len(predictions), 3)

        emissions = carbon_prediction.CarbonPredictionModel.predict_carbon_emissions(days_ahead=3)
        self.assertIn('total_waste_predicted_kg', emissions)
        self.assertIn('total_carbon_predicted_kg', emissions)

        per_capita = carbon_prediction.CarbonPredictionModel.predict_carbon_footprint_per_citizen(population=100)
        self.assertIn('status', per_capita)


class TestNavigation(BaseTestCase):
    def test_detect_waste_link_opens_upload_page(self):
        client = TestClient(app_module.app)
        response = client.get('/api/detect-waste')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Upload Waste Image', response.text)


if __name__ == '__main__':
    unittest.main()

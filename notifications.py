"""
Notification System Module
Handles Email, SMS, and WhatsApp notifications
"""

import sqlite3
from datetime import datetime
from typing import List, Optional
import smtplib
from database import get_connection
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class NotificationManager:
    """Manage all types of notifications"""
    
    # SMTP Configuration (use environment variables in production)
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    EMAIL_ADDRESS = "rcpi.waste.ai@gmail.com"
    EMAIL_PASSWORD = "your_app_password_here"  # Use app-specific password
    
    # SMS/WhatsApp API Configuration
    TWILIO_ACCOUNT_SID = "your_twilio_sid"
    TWILIO_AUTH_TOKEN = "your_twilio_token"
    TWILIO_PHONE = "+1234567890"
    
    @staticmethod
    def create_notification_tables():
        """Create notification tracking tables"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                subject TEXT,
                message TEXT,
                recipient TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                email_enabled INTEGER DEFAULT 1,
                sms_enabled INTEGER DEFAULT 0,
                whatsapp_enabled INTEGER DEFAULT 0,
                push_enabled INTEGER DEFAULT 1,
                notify_complaint_update INTEGER DEFAULT 1,
                notify_collection_schedule INTEGER DEFAULT 1,
                notify_alerts INTEGER DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def send_email(user_id: int, recipient_email: str, subject: str, body: str) -> bool:
        """Send email notification"""
        try:
            # Create email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = NotificationManager.EMAIL_ADDRESS
            msg['To'] = recipient_email
            
            # Create HTML email body
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; background-color: #f5f5f5;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px;">
                        <img src="https://via.placeholder.com/200x50/667eea/764ba2?text=RCPI+Waste+AI" style="width: 200px; margin-bottom: 20px;">
                        <div style="padding: 20px; background-color: #f9f9f9; border-left: 4px solid #667eea;">
                            {body}
                        </div>
                        <p style="margin-top: 20px; color: #999; font-size: 12px;">
                            This is an automated message from RCPI Waste Management System.<br>
                            Please do not reply to this email.
                        </p>
                    </div>
                </body>
            </html>
            """
            
            part = MIMEText(html_body, 'html')
            msg.attach(part)
            
            # Send via SMTP (commented for security - implement with proper credentials)
            # with smtplib.SMTP(NotificationManager.SMTP_SERVER, NotificationManager.SMTP_PORT) as server:
            #     server.starttls()
            #     server.login(NotificationManager.EMAIL_ADDRESS, NotificationManager.EMAIL_PASSWORD)
            #     server.sendmail(NotificationManager.EMAIL_ADDRESS, recipient_email, msg.as_string())
            
            # For now, log to database
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notifications (user_id, type, subject, message, recipient, status, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, 'EMAIL', subject, body[:500], recipient_email, 'sent', datetime.now()))
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            # Log failure
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO notifications (user_id, type, subject, message, recipient, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, 'EMAIL', subject, str(e), recipient_email, 'failed'))
                conn.commit()
                conn.close()
            except:
                pass
            return False
    
    @staticmethod
    def send_sms(user_id: int, phone_number: str, message: str) -> bool:
        """Send SMS notification via Twilio"""
        try:
            # In production, use Twilio API:
            # from twilio.rest import Client
            # client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            # client.messages.create(
            #     to=phone_number,
            #     from_=TWILIO_PHONE,
            #     body=message
            # )
            
            # For now, log to database
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notifications (user_id, type, subject, message, recipient, status, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, 'SMS', 'SMS Notification', message[:160], phone_number, 'sent', datetime.now()))
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            return False
    
    @staticmethod
    def send_whatsapp(user_id: int, phone_number: str, message: str) -> bool:
        """Send WhatsApp notification via Twilio"""
        try:
            # In production, use Twilio WhatsApp API:
            # from twilio.rest import Client
            # client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            # client.messages.create(
            #     to=f"whatsapp:{phone_number}",
            #     from_=f"whatsapp:{TWILIO_PHONE}",
            #     body=message
            # )
            
            # For now, log to database
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notifications (user_id, type, subject, message, recipient, status, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, 'WHATSAPP', 'WhatsApp Message', message, phone_number, 'sent', datetime.now()))
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            return False
    
    @staticmethod
    def notify_complaint_update(complaint_id: int, status: str, user_id: int) -> bool:
        """Notify user about complaint status update"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get complaint details
            cursor.execute('SELECT name, email, phone FROM complaints WHERE id = ?', (complaint_id,))
            complaint = cursor.fetchone()
            
            if not complaint:
                conn.close()
                return False
            
            name, email, phone = complaint
            
            # Create notification message
            subject = f"Your Complaint #{complaint_id} Status: {status.upper()}"
            body = f"""
            <h2>Complaint Status Update</h2>
            <p>Dear {name},</p>
            <p>Your complaint #{complaint_id} has been updated.</p>
            <p><strong>Current Status:</strong> {status.upper()}</p>
            <p>Thank you for reporting. We will continue to work on resolving your issue.</p>
            """
            
            # Get notification preferences
            cursor.execute('''
                SELECT email_enabled, sms_enabled, whatsapp_enabled 
                FROM notification_preferences 
                WHERE user_id = ?
            ''', (user_id,))
            prefs = cursor.fetchone()
            
            sent = False
            if prefs:
                email_enabled, sms_enabled, whatsapp_enabled = prefs
                
                if email_enabled and email:
                    sent = NotificationManager.send_email(user_id, email, subject, body) or sent
                
                if sms_enabled and phone:
                    sms_body = f"Your complaint #{complaint_id} status: {status}. Thank you!"
                    sent = NotificationManager.send_sms(user_id, phone, sms_body) or sent
                
                if whatsapp_enabled and phone:
                    sent = NotificationManager.send_whatsapp(user_id, phone, sms_body) or sent
            
            conn.close()
            return sent
        
        except Exception as e:
            return False
    
    @staticmethod
    def notify_collection_schedule(ward_id: int, collection_date: str) -> bool:
        """Notify ward residents about collection schedule"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get ward residents
            cursor.execute('''
                SELECT id, email, phone FROM users 
                WHERE ward_id = ? AND is_active = 1
            ''', (ward_id,))
            
            residents = cursor.fetchall()
            
            subject = f"Waste Collection Schedule - {collection_date}"
            body = f"""
            <h2>Waste Collection Notice</h2>
            <p>Waste collection is scheduled for <strong>{collection_date}</strong> in your ward.</p>
            <p>Please ensure your waste bins are ready for collection.</p>
            <p>Thank you for your cooperation!</p>
            """
            
            sent_count = 0
            for resident_id, email, phone in residents:
                if email:
                    NotificationManager.send_email(resident_id, email, subject, body)
                    sent_count += 1
            
            conn.close()
            return sent_count > 0
        
        except Exception as e:
            return False
    
    @staticmethod
    def set_notification_preferences(user_id: int, **preferences) -> bool:
        """Update notification preferences for user"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Insert or update preferences
            cursor.execute('''
                INSERT INTO notification_preferences (user_id, email_enabled, sms_enabled, 
                                                     whatsapp_enabled, push_enabled,
                                                     notify_complaint_update, 
                                                     notify_collection_schedule,
                                                     notify_alerts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    email_enabled = excluded.email_enabled,
                    sms_enabled = excluded.sms_enabled,
                    whatsapp_enabled = excluded.whatsapp_enabled,
                    push_enabled = excluded.push_enabled,
                    notify_complaint_update = excluded.notify_complaint_update,
                    notify_collection_schedule = excluded.notify_collection_schedule,
                    notify_alerts = excluded.notify_alerts
            ''', (
                user_id,
                preferences.get('email_enabled', 1),
                preferences.get('sms_enabled', 0),
                preferences.get('whatsapp_enabled', 0),
                preferences.get('push_enabled', 1),
                preferences.get('notify_complaint_update', 1),
                preferences.get('notify_collection_schedule', 1),
                preferences.get('notify_alerts', 1)
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            return False

# Initialize notification tables
NotificationManager.create_notification_tables()

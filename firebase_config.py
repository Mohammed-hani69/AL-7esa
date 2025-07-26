import json
import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FirebaseConfig:
    def __init__(self):
        self.app = None
        self.db = None
        self.initialized = False
        self.google_oauth_config = None
        self.client_config = {
            "apiKey": "AIzaSyCB_GPRRlb6BCe1Mlv7rTIbtnD-Y3vpAj8",
            "authDomain": "al-7esa.firebaseapp.com",
            "databaseURL": "https://al-7esa-default-rtdb.firebaseio.com",
            "projectId": "al-7esa",
            "storageBucket": "al-7esa.firebasestorage.app",
            "messagingSenderId": "893628750909",
            "appId": "1:893628750909:web:3cd09924c12987b3ef9e54",
            "measurementId": "G-B026ZL6KXG"
        }
        self._load_google_oauth_config()
    
    def initialize(self):
        if not self.initialized:
            try:
                # تحقق من ملف الاعتماد
                cred_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY', 'firebase-service-account.json')
                
                if os.path.exists(cred_path):
                    try:
                        # Read and validate service account file
                        with open(cred_path, 'r', encoding='utf-8') as f:
                            service_account_data = json.load(f)
                        
                        # Check if it's a real service account file
                        if (service_account_data.get('private_key') and 
                            not service_account_data['private_key'].startswith('YOUR_') and
                            service_account_data.get('client_email') and
                            not service_account_data['client_email'].startswith('firebase-adminsdk-xxxxx')):
                            
                            cred = credentials.Certificate(cred_path)
                            self.app = firebase_admin.initialize_app(cred)
                            self.db = firestore.client()
                            self.initialized = True
                            logger.info("Firebase Admin SDK initialized successfully with service account")
                        else:
                            logger.warning("Service account file contains placeholder data - Firebase Admin disabled")
                            logger.info("Firebase Admin SDK service account not found. Using REST API for authentication.")
                            
                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning(f"Invalid service account file: {e}")
                        logger.info("Firebase Admin SDK service account not found. Using REST API for authentication.")
                        
                else:
                    logger.warning(f"Firebase service account file not found: {cred_path}")
                    logger.info("Firebase Admin SDK service account not found. Using REST API for authentication.")
                    
                # Always enable client-side auth
                logger.info("Firebase client configuration found. Client-side authentication enabled.")
                    
            except Exception as e:
                logger.error(f"Firebase initialization error: {e}")
                logger.info("Firebase Admin SDK service account not found. Using REST API for authentication.")
                logger.info("Firebase client configuration found. Client-side authentication enabled.")
    
    def _load_google_oauth_config(self):
        """تحميل إعدادات Google OAuth من الملف"""
        try:
            config_path = 'google_oauth_config.json'
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.google_oauth_config = json.load(f)
                logger.info("Google OAuth configuration loaded successfully")
            else:
                logger.warning("Google OAuth configuration file not found")
        except Exception as e:
            logger.error(f"Error loading Google OAuth config: {e}")
    
    def get_google_client_id(self):
        """الحصول على Google Client ID حسب البيئة"""
        try:
            if not self.google_oauth_config:
                return None
            
            # استخدام إعدادات الإنتاج إذا كان النطاق al-7esa.com
            if self.google_oauth_config.get('web'):
                return self.google_oauth_config['web']['client_id']
            
            return None
        except Exception as e:
            logger.error(f"Error getting Google Client ID: {e}")
            return None
    
    def get_google_oauth_settings(self):
        """الحصول على جميع إعدادات Google OAuth"""
        if not self.google_oauth_config:
            return None
        
        return self.google_oauth_config.get('web', {})
    
    def is_production_domain(self, request_host):
        """تحديد ما إذا كان النطاق للإنتاج"""
        production_domains = ['al-7esa.com', 'www.al-7esa.com']
        return request_host in production_domains
    
    def get_client_config(self):
        """إرجاع تكوين Firebase للعميل (JavaScript)"""
        return self.client_config
    
    def verify_phone_token(self, id_token):
        """التحقق من رمز الهاتف"""
        try:
            if not self.initialized:
                self.initialize()
            
            if not self.app:
                logger.error("Firebase Admin SDK not initialized")
                return None
                
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    def get_user_by_uid(self, uid):
        """الحصول على مستخدم بواسطة UID"""
        try:
            if not self.initialized:
                self.initialize()
            
            if not self.app:
                logger.error("Firebase Admin SDK not initialized")
                return None
                
            user_record = auth.get_user(uid)
            return user_record
        except Exception as e:
            logger.error(f"Get user error: {e}")
            return None
    
    def get_firestore_client(self):
        """الحصول على عميل Firestore"""
        if not self.initialized:
            self.initialize()
        return self.db

# إنشاء مثيل عام
firebase_config = FirebaseConfig()

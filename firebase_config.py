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
    
    def initialize(self):
        if not self.initialized:
            try:
                # تحقق من ملف الاعتماد
                cred_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY', 'firebase-service-account.json')
                
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    self.app = firebase_admin.initialize_app(cred)
                    self.db = firestore.client()
                    self.initialized = True
                    logger.info("Firebase Admin SDK initialized successfully with service account")
                else:
                    logger.warning(f"Firebase service account file not found: {cred_path}")
                    logger.info("Firebase Admin SDK service account not found. Using REST API for authentication.")
                    logger.info("Firebase client configuration found. Client-side authentication enabled.")
                    
            except Exception as e:
                logger.error(f"Firebase initialization error: {e}")
    
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

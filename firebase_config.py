import firebase_admin
from firebase_admin import credentials, auth
import os

class FirebaseConfig:
    def __init__(self):
        self.app = None
        self.initialized = False
    
    def initialize(self):
        if not self.initialized:
            try:
                # تحقق من ملف الاعتماد
                cred_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY', 'firebase-service-account.json')
                
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    self.app = firebase_admin.initialize_app(cred)
                    self.initialized = True
                    print("Firebase initialized successfully")
                else:
                    print(f"Firebase service account file not found: {cred_path}")
                    
            except Exception as e:
                print(f"Firebase initialization error: {e}")
    
    def verify_phone_token(self, id_token):
        """التحقق من رمز الهاتف"""
        try:
            if not self.initialized:
                self.initialize()
            
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            print(f"Token verification error: {e}")
            return None
    
    def get_user_by_uid(self, uid):
        """الحصول على مستخدم بواسطة UID"""
        try:
            if not self.initialized:
                self.initialize()
            
            user_record = auth.get_user(uid)
            return user_record
        except Exception as e:
            print(f"Get user error: {e}")
            return None

# إنشاء مثيل عام
firebase_config = FirebaseConfig()

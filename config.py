import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get("SESSION_SECRET", "al-hesa-default-secret")
    DEBUG = os.environ.get("FLASK_ENV", "development") == "development"
    
    # Environment detection
    IS_PRODUCTION = os.environ.get("FLASK_ENV") == "production"

    # CSRF Configuration - DISABLED per user request
    # User explicitly requested: "لا اريد استخدام CSRF في التسجيل و في انشاء الحساب"
    WTF_CSRF_TIME_LIMIT = None  # No time limit for CSRF tokens
    WTF_CSRF_SSL_STRICT = False  # Allow HTTP in development
    WTF_CSRF_ENABLED = False  # DISABLED for authentication endpoints
    WTF_CSRF_CHECK_DEFAULT = False  # DISABLED for authentication endpoints
    
    # Session Configuration - محسن لحل مشكلة عدم استمرار الجلسة
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # 7 days session lifetime
    SESSION_COOKIE_SECURE = IS_PRODUCTION  # True for HTTPS in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'al_7esa_session'  # اسم مخصص للجلسة
    SESSION_COOKIE_PATH = '/'  # مسار الجلسة
    SESSION_TYPE = 'filesystem'  # نوع الجلسة
    SESSION_PERMANENT = True  # جعل الجلسة دائمة افتراضياً
    SESSION_USE_SIGNER = True  # توقيع الجلسة للأمان
    SESSION_KEY_PREFIX = 'al_7esa:'  # بادئة مفتاح الجلسة
    
    # Domain configuration based on environment
    if IS_PRODUCTION:
        SESSION_COOKIE_DOMAIN = '.al-7esa.com'  # Allow cookies for al-7esa.com and www.al-7esa.com
    else:
        SESSION_COOKIE_DOMAIN = None  # Default for localhost

    # CORS Configuration
    CORS_ORIGINS = [
        "https://al-7esa.com",
        "https://www.al-7esa.com",
        "http://127.0.0.1:5000"  # للتطوير المحلي
    ]
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'X-CSRFToken', 'X-Requested-With']
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']
    
    # Rate Limiting Configuration
    RATE_LIMIT_STORAGE_URI = os.environ.get('RATE_LIMIT_STORAGE_URI', 'memory://')
    RATE_LIMIT_WHITELIST = os.environ.get('RATE_LIMIT_WHITELIST', '').split(',') if os.environ.get('RATE_LIMIT_WHITELIST') else []
    
    # في بيئة الإنتاج، استخدم Redis للـ Rate Limiting
    if os.environ.get('FLASK_ENV') == 'production':
        RATE_LIMIT_STORAGE_URI = os.environ.get('REDIS_URL', 'redis://localhost:6379')

    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///al-7esa.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # Firebase Configuration
    FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY", "AIzaSyCB_GPRRlb6BCe1Mlv7rTIbtnD-Y3vpAj8")
    FIREBASE_AUTH_DOMAIN = os.environ.get("FIREBASE_AUTH_DOMAIN", "al-7esa.firebaseapp.com")
    FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "al-7esa")
    FIREBASE_STORAGE_BUCKET = os.environ.get("FIREBASE_STORAGE_BUCKET", "al-7esa.appspot.com")
    FIREBASE_MESSAGING_SENDER_ID = os.environ.get("FIREBASE_MESSAGING_SENDER_ID", "893628750909")
    FIREBASE_APP_ID = os.environ.get("FIREBASE_APP_ID", "1:893628750909:web:3cd09924c12987b3ef9e54")
    FIREBASE_MEASUREMENT_ID = os.environ.get("FIREBASE_MEASUREMENT_ID", "G-B026ZL6KXG")
    FIREBASE_DATABASE_URL = os.environ.get("FIREBASE_DATABASE_URL", "https://al-7esa-default-rtdb.firebaseio.com")

    # Firebase Admin SDK Configuration
    FIREBASE_SERVICE_ACCOUNT_PATH = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    FIREBASE_SERVER_KEY = os.environ.get("FIREBASE_SERVER_KEY")

    @property
    def FIREBASE_CONFIG(self):
        """Get Firebase configuration as dictionary for client-side use"""
        return {
            'apiKey': self.FIREBASE_API_KEY,
            'authDomain': self.FIREBASE_AUTH_DOMAIN,
            'projectId': self.FIREBASE_PROJECT_ID,
            'storageBucket': self.FIREBASE_STORAGE_BUCKET,
            'messagingSenderId': self.FIREBASE_MESSAGING_SENDER_ID,
            'appId': self.FIREBASE_APP_ID,
            'measurementId': self.FIREBASE_MEASUREMENT_ID,
            'databaseURL': self.FIREBASE_DATABASE_URL
        }

    # Payment Configuration
    PAYMENT_CURRENCY = "EGP"  

    # Application Configuration
    DEFAULT_TRIAL_DAYS = 7
    UPLOAD_FOLDER = "static/uploads"
    
    # File Upload Configuration - حدود عالية جداً للملفات الكبيرة
    MAX_CONTENT_LENGTH = None  # بدون حد أقصى للحجم نهائياً
    
    # File size limits by type - أحجام عالية جداً محدثة
    FILE_SIZE_LIMITS = {
        'image': 200 * 1024 * 1024,     # 200MB للصور
        'video': 2048 * 1024 * 1024,    # 2GB للفيديو
        'audio': 500 * 1024 * 1024,     # 500MB للصوت
        'file': 500 * 1024 * 1024       # 500MB للمستندات
    }
    
    # إعدادات محسنة لرفع الملفات الكبيرة
    USE_X_ACCEL_REDIRECT = True
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    STATIC_FOLDER = os.path.join(basedir, 'static')
    CHUNK_SIZE = 1024 * 1024  # 1MB حجم القطعة للتدفق (محسن)

    # المجلدات الفرعية للتحميلات
    UPLOAD_FOLDERS = {
        'classroom_content': os.path.join(STATIC_FOLDER, 'uploads', 'classroom_content'),
        'assignments': os.path.join(STATIC_FOLDER, 'uploads', 'assignments'),
        'profile_pics': os.path.join(STATIC_FOLDER, 'uploads', 'profile_pics'),
    }

    # أنواع الملفات المسموح بها - Enhanced
    ALLOWED_VIDEO_EXTENSIONS = ['mp4', 'webm', 'mov', 'avi']
    ALLOWED_AUDIO_EXTENSIONS = ['mp3', 'wav', 'ogg', 'm4a']
    ALLOWED_DOCUMENT_EXTENSIONS = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'ppt', 'pptx']
    ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp']
    
    # All allowed extensions combined
    ALLOWED_EXTENSIONS = set(
        ALLOWED_VIDEO_EXTENSIONS + 
        ALLOWED_AUDIO_EXTENSIONS + 
        ALLOWED_DOCUMENT_EXTENSIONS + 
        ALLOWED_IMAGE_EXTENSIONS
    )


class DevelopmentConfig(Config):
    """تكوين بيئة التطوير"""
    DEBUG = True
    # في بيئة التطوير، نسمح بالمصادر المحلية
    CORS_ORIGINS = [
        "http://127.0.0.1:5000", 
        "http://localhost:5000",
        "http://127.0.0.1:3000",  # للتطوير مع React/Next.js
        "http://localhost:3000"
    ]


class ProductionConfig(Config):
    """تكوين بيئة الإنتاج مع إعدادات CORS آمنة"""
    DEBUG = False
    
    # إعدادات أمان إضافية للإنتاج
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'X-CSRFToken', 'X-Requested-With']
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']  # إزالة PATCH إذا لم يكن مطلوباً
    CORS_MAX_AGE = 3600  # مدة تخزين preflight requests
    
    # في الإنتاج، يجب تحديد المصادر المسموحة بدقة
    CORS_ORIGINS = [
        "https://al-7esa.com",
        "https://www.al-7esa.com"
    ]


class TestingConfig(Config):
    """تكوين بيئة الاختبار"""
    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False  # تعطيل CSRF للاختبارات
    CORS_ORIGINS = [
        "http://localhost", 
        "http://127.0.0.1",
        "http://localhost:5000",
        "http://127.0.0.1:5000"
    ]


# معالج اختيار التكوين حسب البيئة
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
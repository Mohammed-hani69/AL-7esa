import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get("SESSION_SECRET", "al-hesa-default-secret")
    DEBUG = os.environ.get("FLASK_ENV", "development") == "development"

    # CSRF Configuration
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour in seconds

    # CORS Configuration
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",") if os.environ.get("CORS_ORIGINS") else ["*"]
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
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size

    # إعدادات خدمة الملفات
    USE_X_ACCEL_REDIRECT = True
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    STATIC_FOLDER = os.path.join(basedir, 'static')
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB
    CHUNK_SIZE = 8192  # حجم القطعة للتدفق

    # المجلدات الفرعية للتحميلات
    UPLOAD_FOLDERS = {
        'classroom_content': os.path.join(STATIC_FOLDER, 'uploads', 'classroom_content'),
        'assignments': os.path.join(STATIC_FOLDER, 'uploads', 'assignments'),
        'profile_pics': os.path.join(STATIC_FOLDER, 'uploads', 'profile_pics'),
    }

    # أنواع الملفات المسموح بها
    ALLOWED_VIDEO_EXTENSIONS = ['mp4', 'webm', 'ogg']
    ALLOWED_AUDIO_EXTENSIONS = ['mp3', 'wav', 'ogg']
    ALLOWED_DOCUMENT_EXTENSIONS = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt']
    ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif']


class DevelopmentConfig(Config):
    """تكوين بيئة التطوير"""
    DEBUG = True
    # في بيئة التطوير، نسمح بجميع المصادر لسهولة التطوير
    CORS_ORIGINS = ["*"]


class ProductionConfig(Config):
    """تكوين بيئة الإنتاج مع إعدادات CORS آمنة"""
    DEBUG = False
    
    # في الإنتاج، يجب تحديد المصادر المسموحة بدقة
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "https://yourdomain.com,https://www.yourdomain.com").split(",")
    
    # إعدادات أمان إضافية للإنتاج
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'X-CSRFToken', 'X-Requested-With']
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']  # إزالة PATCH إذا لم يكن مطلوباً
    CORS_MAX_AGE = 3600  # مدة تخزين preflight requests
    
    # منع CORS wildcards في الإنتاج
    @property
    def CORS_ORIGINS(self):
        origins = os.environ.get("CORS_ORIGINS", "").split(",")
        # تصفية وإزالة أي wildcards
        filtered_origins = [origin.strip() for origin in origins if origin.strip() and origin.strip() != "*"]
        if not filtered_origins:
            # إذا لم تكن هناك مصادر محددة، استخدم localhost فقط كاحتياط آمن
            return ["http://localhost:5000", "https://localhost:5000"]
        return filtered_origins


class TestingConfig(Config):
    """تكوين بيئة الاختبار"""
    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False  # تعطيل CSRF للاختبارات
    CORS_ORIGINS = ["http://localhost", "http://127.0.0.1"]
    CORS_ORIGINS = ["http://localhost", "http://127.0.0.1"]


# معالج اختيار التكوين حسب البيئة
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
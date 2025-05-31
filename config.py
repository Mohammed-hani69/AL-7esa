import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get("SESSION_SECRET", "al-hesa-default-secret")
    DEBUG = True

    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///al-7esa.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }


    # Firebase Configuration
    FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY", "")
    FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "")
    FIREBASE_APP_ID = os.environ.get("FIREBASE_APP_ID", "")

    # Payment Configuration
    PAYMENT_CURRENCY = "SAR"  # Saudi Riyal

    # Application Configuration
    DEFAULT_TRIAL_DAYS = 14
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
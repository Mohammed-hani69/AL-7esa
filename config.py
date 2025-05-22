import os


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
"""
إعدادات Google OAuth
"""
import os

GOOGLE_CONFIG = {
    "web": {
        "client_id": "34251820592-4mrp3l1tna1qv7a5gt547hfcphokiu4c.apps.googleusercontent.com",
        "project_id": "al-7esa-466912",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "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",
        "redirect_uris": [
            "https://al-7esa.com/auth/google/callback",
            "http://127.0.0.1:5000/auth/google/callback",
            "https://www.al-7esa.com/auth/google/callback"
        ],
        "javascript_origins": [
            "https://al-7esa.com",
            "https://www.al-7esa.com",
            "http://127.0.0.1:5000"
        ]
    }
}

# استخراج المعرفات المطلوبة
GOOGLE_CLIENT_ID = GOOGLE_CONFIG["web"]["client_id"]
GOOGLE_CLIENT_SECRET = GOOGLE_CONFIG["web"]["client_secret"]

# تحديد الـ redirect URI بناءً على البيئة
IS_PRODUCTION = os.environ.get("FLASK_ENV") == "production"
if IS_PRODUCTION:
    GOOGLE_REDIRECT_URI = "https://al-7esa.com/auth/google/callback"  # للنطاق الحقيقي
else:
    GOOGLE_REDIRECT_URI = "http://127.0.0.1:5000/auth/google/callback"  # للتطوير المحلي

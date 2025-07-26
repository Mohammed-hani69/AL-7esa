"""
إعدادات Google OAuth للتطوير المحلي
"""

# إعدادات مؤقتة للتطوير المحلي
GOOGLE_DEV_CONFIG = {
    "web": {
        "client_id": "34251820592-4mrp3l1tna1qv7a5gt547hfcphokiu4c.apps.googleusercontent.com",
        "project_id": "al-7esa-466912",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "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",
        "redirect_uris": [
            "http://localhost:5000/auth/google/callback",
            "http://127.0.0.1:5000/auth/google/callback"
        ],
        "javascript_origins": [
            "http://localhost:5000",
            "http://127.0.0.1:5000"
        ]
    }
}

# معرف العميل للتطوير المحلي
GOOGLE_DEV_CLIENT_ID = GOOGLE_DEV_CONFIG["web"]["client_id"]
GOOGLE_DEV_CLIENT_SECRET = GOOGLE_DEV_CONFIG["web"]["client_secret"]

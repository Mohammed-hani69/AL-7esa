"""
Jitsi Meet self-hosted server configuration
"""

# Jitsi Meet server configuration
from os import getenv

# Domain configuration with fallback
JITSI_DOMAIN = getenv('JITSI_DOMAIN', 'meet.jit.si')  # Allow custom domain via environment variable
JITSI_PROTOCOL = getenv('JITSI_PROTOCOL', 'https')  # Protocol (http/https)
JITSI_APP_ID = getenv('JITSI_APP_ID', 'al7esa-app')  # App ID for JWT auth
JITSI_APP_SECRET = getenv('JITSI_APP_SECRET', 'n3VkmQ60YnegwV4Vh2GZRCuYbWgn6oWd')  # 32-char secret key for JWT auth

# Room configuration
JITSI_ROOM_PREFIX = "hsa"  # Fixed prefix for all room names
ROOM_NAME_CHARS = "abcdefghijklmnopqrstuvwxyz"  # Only letters allowed for room names

# Advanced configuration
JITSI_TIMEOUT = 30  # Connection timeout in seconds
JITSI_RETRY_ATTEMPTS = 3  # Number of connection retry attempts

# Security settings
USE_JWT_TOKEN = True  # Enable JWT authentication
ENABLE_LOBBY = True  # Require users to be admitted by moderator
ENABLE_PREJOIN_PAGE = False  # Skip the prejoin page

# Token settings
TOKEN_EXPIRY = 24 * 60 * 60  # 24 hours in seconds
TOKEN_ALGO = "HS256"  # HMAC-SHA256 algorithm for JWT

# Default interface configuration
DEFAULT_CONFIG = {
    'startWithAudioMuted': True,  # Start muted by default
    'startWithVideoMuted': True,  # Start without video by default
    'prejoinPageEnabled': False,
    'disableDeepLinking': True,
    'enableClosePage': False,
    'enableWelcomePage': False,
    'defaultLanguage': 'ar',
    'enableNoisyMicDetection': True,
    'enableNoAudioDetection': True,
    'enableLobby': True,
    'resolution': 720,
    'constraints': {
        'video': {
            'height': {
                'ideal': 720,
                'max': 1080,
                'min': 480
            }
        }
    }
}

# Interface configuration for both desktop and mobile
INTERFACE_CONFIG = {
    'SHOW_JITSI_WATERMARK': False,
    'SHOW_WATERMARK_FOR_GUESTS': False,
    'SHOW_BRAND_WATERMARK': False,
    'TOOLBAR_BUTTONS': [
        'microphone', 'camera', 'chat',
        'raisehand', 'videoquality', 'participants-pane', 
        'desktop', 'fullscreen', 'settings', 'hangup'
    ],
    'SETTINGS_SECTIONS': ['devices', 'language', 'moderator'],
    'DEFAULT_REMOTE_DISPLAY_NAME': 'مشارك',
    'DEFAULT_LOCAL_DISPLAY_NAME': 'أنت',
    'LANG_DETECTION': False,
    'DEFAULT_LANGUAGE': 'ar',
    'NATIVE_APP_NAME': 'الحصة',
    'PROVIDER_NAME': 'الحصة',
    'MOBILE_APP_PROMO': False,
    'SHOW_CHROME_EXTENSION_BANNER': False,
    'DISABLE_JOIN_LEAVE_NOTIFICATIONS': True,
    'RECENT_LIST_ENABLED': False,
    'ENABLE_FEEDBACK_ANIMATION': False,
    'DISPLAY_WELCOME_PAGE_CONTENT': False,
    'DISPLAY_WELCOME_PAGE_TOOLBAR_ADDITIONAL_CONTENT': False
}

"""
Utility functions for general platform utilities
"""
import re
import secrets
import string
from datetime import datetime
from urllib.parse import urlparse, urlencode

def generate_room_name(prefix="room"):
    """
    Generate a secure room name:
    - Format: prefix-randomstring
    - Random string uses letters and numbers
    - Returns a URL-safe room name
    """
    # Generate 12 random chars 
    alphabet = string.ascii_lowercase + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(12))
    
    # Combine with prefix
    return f"{prefix}-{random_part}"

def generate_classroom_room_name(classroom_id, user_type="room"):
    """
    Generate a unique room name for a specific classroom
    Format: hsa-classroom{id}-{user_type}-{random}
    """
    alphabet = string.ascii_lowercase + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(8))
    
    return f"hsa-classroom{classroom_id}-{user_type}-{random_part}"

def cleanup_expired_streams():
    """
    Clean up expired live streams that are still marked as active.
    This function should be called periodically to ensure expired streams are properly ended.
    Returns the number of streams that were cleaned up.
    """
    from models import LiveStream, db
    
    # Find all active streams that have expired
    expired_streams = LiveStream.query.filter(
        LiveStream.is_active == True,
        LiveStream.auto_end_at < datetime.utcnow()
    ).all()
    
    cleaned_count = 0
    for stream in expired_streams:
        if stream.is_expired:
            stream.end_stream()
            cleaned_count += 1
    
    if cleaned_count > 0:
        print(f"Cleaned up {cleaned_count} expired live streams")
    
    return cleaned_count

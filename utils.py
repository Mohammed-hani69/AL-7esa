"""
Utility functions for URL validation and room code generation for Jitsi Meet
"""
import re
import secrets
import string
from urllib.parse import urlparse, urlencode
from config import JITSI_DOMAIN, JITSI_PROTOCOL

def generate_room_name(prefix="room"):
    """
    Generate a secure room name for Jitsi Meet:
    - Format: prefix-randomstring
    - Random string uses letters and numbers
    - Returns a URL-safe room name
    """
    # Generate 12 random chars 
    alphabet = string.ascii_lowercase + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(12))
    
    # Combine with prefix
    return f"{prefix}-{random_part}"

def is_valid_jitsi_room_name(room_name):
    """
    Validate a Jitsi room name format
    - Must be alphanumeric with hyphens
    - 4-64 characters long
    """
    if not room_name or not isinstance(room_name, str):
        return False
        
    # Only allow letters, numbers, and hyphens
    if not re.match(r'^[a-z0-9-]+$', room_name):
        return False
        
    # Check length
    if not (4 <= len(room_name) <= 64):
        return False
        
    return True

def is_valid_jitsi_url(url):
    """
    Validate that a URL is a proper Jitsi Meet URL
    Format: https://domain/roomname[?jwt=token]
    """
    if not url or not isinstance(url, str):
        return False
        
    try:
        parsed = urlparse(url)
        
        # Validate URL components
        if not all([
            parsed.scheme in ('http', 'https'),
            parsed.netloc == JITSI_DOMAIN,
            parsed.path.startswith('/')
        ]):
            return False
            
        # Extract and validate the room name
        room_name = parsed.path.strip('/')
        return is_valid_jitsi_room_name(room_name)
    except:
        return False

def clean_room_name(name):
    """
    Clean a room name to match Jitsi Meet requirements:
    - Alphanumeric with hyphens only
    - Lowercase
    - 4-64 characters
    Returns None if the name cannot be properly cleaned
    """
    if not name or not isinstance(name, str):
        return None
        
    # Convert to lowercase and replace spaces with hyphens
    clean = name.lower().replace(' ', '-')
    
    # Keep only allowed chars
    clean = ''.join(c for c in clean if c.isalnum() or c == '-')
    
    # Remove consecutive hyphens
    clean = re.sub(r'-+', '-', clean)
    
    # Remove leading/trailing hyphens
    clean = clean.strip('-')
    
    # Validate length
    if not (4 <= len(clean) <= 64):
        return None
        
    return clean if is_valid_jitsi_room_name(clean) else None

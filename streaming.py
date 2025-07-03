# Import dependencies
from flask import Flask, request, session, url_for
from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room, leave_room
from random import choices
from string import ascii_lowercase
from collections import deque
import time
import weakref
import jwt
from datetime import datetime
import time
import weakref
import jwt
import requests
from requests.exceptions import RequestException

# Import app and extensions
from app import app, db, socketio

# Import models
from models import User, Classroom

# Import Jitsi configuration
from jitsi_config import (
    JITSI_DOMAIN,
    JITSI_PROTOCOL,
    JITSI_ROOM_PREFIX,
    USE_JWT_TOKEN,
    DEFAULT_CONFIG,
    INTERFACE_CONFIG,
    JITSI_APP_ID,
    JITSI_APP_SECRET,
    JITSI_RETRY_ATTEMPTS,
    JITSI_TIMEOUT
)

# State management
active_streams = {}  # {classroom_id: StreamSession}
room_participants = {}  # {classroom_id: set(user_ids)}
session_states = {}  # {classroom_id: {'participants': {}, 'is_active': bool}}

class StreamSession:
    """Helper class to manage stream sessions"""
    def __init__(self, room_name, teacher_id, url, token=None):
        self.room_name = room_name
        self.teacher_id = teacher_id
        self.url = url
        self.token = token
        self.start_time = time.time()
        self.connection_status = 'connecting'
        self.retry_count = 0
        self.connection_check = time.time()
    
    def to_dict(self):
        return {
            'room_name': self.room_name,
            'teacher_id': self.teacher_id,
            'url': self.url,
            'token': self.token,
            'start_time': self.start_time,
            'connection_status': self.connection_status
        }

# Enhanced session and cache management
class SessionInfo:
    """Wrapper class to allow weak references to session data"""
    def __init__(self, data):
        self.data = data

class SessionManager:
    def __init__(self):
        self._sessions = {}  # Changed from WeakValueDictionary to regular dict
        self._message_cache = {}
        self._connection_status = {}
        self._reconnection_attempts = {}
        self.MAX_CACHE_SIZE = 100
        self.CLEANUP_INTERVAL = 300  # 5 minutes
        self.MAX_RECONNECT_ATTEMPTS = 5
        self.RECONNECT_DELAY = 3  # seconds
        self._last_cleanup = time.time()

    def _cleanup_old_sessions(self):
        """Clean up inactive sessions"""
        current_time = time.time()
        if current_time - self._last_cleanup < self.CLEANUP_INTERVAL:
            return

        self._last_cleanup = current_time
        timeout = current_time - self.CLEANUP_INTERVAL
        
        to_remove = []
        for classroom_id, session in self._sessions.items():
            if session.data['last_activity'] < timeout:
                to_remove.append(classroom_id)
                
        for classroom_id in to_remove:
            del self._sessions[classroom_id]
            if classroom_id in self._connection_status:
                del self._connection_status[classroom_id]
            if classroom_id in self._reconnection_attempts:
                del self._reconnection_attempts[classroom_id]

    def init_session(self, classroom_id):
        """Initialize or update a session"""
        self._cleanup_old_sessions()
        
        if classroom_id not in self._sessions:
            session_data = {
                'participants': {},
                'is_active': True,
                'last_activity': time.time(),
                'messages': deque(maxlen=self.MAX_CACHE_SIZE),
                'stream_quality': {
                    'video': 'high',
                    'audio': 'high'
                }
            }
            self._sessions[classroom_id] = SessionInfo(session_data)
        else:
            self._sessions[classroom_id].data['last_activity'] = time.time()

        if classroom_id not in self._connection_status:
            self._connection_status[classroom_id] = {}
        if classroom_id not in self._reconnection_attempts:
            self._reconnection_attempts[classroom_id] = {}
            
    def cache_message(self, classroom_id, message):
        """Cache a message for a classroom"""
        self.init_session(classroom_id)
        self._sessions[classroom_id].data['messages'].append(message)
        self._sessions[classroom_id].data['last_activity'] = time.time()
        
    def get_cached_messages(self, classroom_id):
        """Get cached messages for a classroom"""
        self.init_session(classroom_id)
        return list(self._sessions[classroom_id].data['messages'])
        
    def update_connection_status(self, classroom_id, user_id, status):
        """Update connection status for a user"""
        self.init_session(classroom_id)
        current_attempts = self._connection_status.get(classroom_id, {}).get(user_id, {}).get('connection_attempts', 0)
        
        self._connection_status[classroom_id][user_id] = {
            'status': status,
            'last_update': time.time(),
            'connection_attempts': current_attempts + 1
        }
        self._sessions[classroom_id].data['last_activity'] = time.time()
        
    def get_connection_status(self, classroom_id, user_id):
        """Get connection status for a user"""
        if classroom_id in self._connection_status:
            return self._connection_status[classroom_id].get(user_id, {})

# Stream state class
class StreamState:
    """Class to safely store stream state data"""
    def __init__(self, data):
        self.data = data
    
    def to_dict(self):
        return self.data

# Initialize managers
session_manager = SessionManager()

class NotificationManager:
    def __init__(self):
        self._notifications = {}
        self._priority_notifications = {}
        self.MAX_NOTIFICATIONS = 50
        
    def add_notification(self, classroom_id, notification_type, data, priority=False):
        if classroom_id not in self._notifications:
            self._notifications[classroom_id] = deque(maxlen=self.MAX_NOTIFICATIONS)
            self._priority_notifications[classroom_id] = deque(maxlen=10)
            
        notification = {
            'type': notification_type,
            'data': data,
            'timestamp': time.time(),
            'priority': priority
        }
        
        if priority:
            self._priority_notifications[classroom_id].append(notification)
        else:
            self._notifications[classroom_id].append(notification)
        
        # إضافة معلومات إضافية للإشعار
        notification.update({
            'classroom_id': classroom_id,
            'notification_id': str(int(time.time() * 1000)),
            'read_by': set(),
            'actions': self._get_notification_actions(notification_type)
        })
        
        # إرسال الإشعار للمشاركين
        socketio.emit('classroom_notification', notification, room=f'classroom_{classroom_id}')
        
    def _get_notification_actions(self, notification_type):
        """تحديد الإجراءات المتاحة لكل نوع إشعار"""
        actions = {
            'stream_started': ['join_stream', 'dismiss'],
            'stream_ended': ['leave_stream', 'dismiss'],
            'user_joined': ['send_welcome', 'dismiss'],
            'user_left': ['dismiss'],
            'connection_issue': ['retry_connection', 'dismiss'],
            'stream_quality': ['adjust_quality', 'dismiss']
        }
        return actions.get(notification_type, ['dismiss'])
        
    def mark_notification_read(self, classroom_id, notification_id, user_id):
        """تحديث حالة قراءة الإشعار"""
        for notifications in [self._notifications, self._priority_notifications]:
            if classroom_id in notifications:
                for notif in notifications[classroom_id]:
                    if notif.get('notification_id') == notification_id:
                        notif['read_by'].add(user_id)
                        break
    
    def get_notifications(self, classroom_id, include_read=False):
        """استرجاع الإشعارات مع خيار تضمين المقروءة"""
        all_notifications = []
        
        if classroom_id in self._priority_notifications:
            all_notifications.extend(list(self._priority_notifications[classroom_id]))
        
        if classroom_id in self._notifications:
            all_notifications.extend(list(self._notifications[classroom_id]))
            
        if not include_read:
            all_notifications = [
                n for n in all_notifications 
                if current_user.id not in n.get('read_by', set())
            ]
            
        return sorted(all_notifications, key=lambda x: x['timestamp'], reverse=True)

notification_manager = NotificationManager()

def generate_jwt_token(user_id, room_name):
    """Generate a JWT token for Jitsi Meet authentication"""
    from jitsi_config import JITSI_APP_SECRET, TOKEN_EXPIRY, TOKEN_ALGO
    
    now = int(time.time())
    payload = {
        "context": {
            "user": {
                "id": str(user_id),
                "name": current_user.name if current_user else "Guest"
            }
        },
        "aud": JITSI_APP_ID,
        "iss": JITSI_APP_ID,
        "sub": JITSI_DOMAIN,
        "room": room_name,
        "exp": now + TOKEN_EXPIRY,
        "iat": now
    }
    
    return jwt.encode(payload, JITSI_APP_SECRET, algorithm=TOKEN_ALGO)

def check_jitsi_connection():
    """Check if the Jitsi server is accessible"""
    try:
        response = requests.get(f"{JITSI_PROTOCOL}://{JITSI_DOMAIN}", timeout=JITSI_TIMEOUT)
        return response.status_code == 200
    except RequestException:
        return False

def generate_jitsi_url(room_name, user_id=None):
    """Generate the full Jitsi Meet URL for a room with optional JWT
    
    Args:
        room_name (str): The name of the Jitsi room
        user_id (str, optional): User ID for JWT token generation
        
    Returns:
        tuple: (url, token) where url is the complete Jitsi Meet URL and token is the JWT if enabled
    """
    base_url = f"{JITSI_PROTOCOL}://{JITSI_DOMAIN}/{room_name}"
    
    if USE_JWT_TOKEN and user_id and current_user.is_authenticated:
        if not JITSI_APP_SECRET:
            raise RuntimeError("JWT authentication enabled but no secret key provided")
            
        token = generate_jwt_token(
            user_id=current_user.id,
            room_name=room_name
        )
        return f"{base_url}?jwt={token}", token
    
    return base_url, None

def generate_jitsi_room_name(classroom_id):
    """Generate a Jitsi Meet room name in the format hsa-xxxx-yyy"""
    seg1 = JITSI_ROOM_PREFIX
    seg2 = ''.join(choices(ascii_lowercase, k=4))
    seg3 = ''.join(choices(ascii_lowercase, k=3))
    return f"{seg1}-{seg2}-{seg3}"

def update_session_state(classroom_id, user_id):
    """Update user's last seen timestamp in a session"""
    if classroom_id not in session_states:
        session_states[classroom_id] = {
            'participants': {},
            'is_active': True
        }
    
    if 'participants' not in session_states[classroom_id]:
        session_states[classroom_id]['participants'] = {}
    
    session_states[classroom_id]['participants'][user_id] = {
        'last_seen': time.time()
    }

def cleanup_inactive_sessions():
    """Remove inactive sessions and their related streams"""
    current_time = time.time()
    inactive_threshold = 300  # 5 minutes
    
    for classroom_id in list(session_states.keys()):
        if 'participants' not in session_states[classroom_id]:
            continue
            
        active_participants = False
        for user_data in session_states[classroom_id]['participants'].values():
            if current_time - user_data['last_seen'] < inactive_threshold:
                active_participants = True
                break
        
        if not active_participants:
            # End stream if it exists
            if classroom_id in active_streams:
                end_stream(classroom_id)
            
            # Clean up session state
            del session_states[classroom_id]

# Stream session management
def start_stream(classroom_id):
    """Start a new streaming session using Jitsi Meet"""
    if classroom_id in active_streams:
        session_dict = active_streams[classroom_id].to_dict()
        if not session_dict['room_name']:
            # If no room name, regenerate it
            del active_streams[classroom_id]
        else:
            return session_dict
        
    try:
        # First generate room name and validate it
        room_name = generate_jitsi_room_name(classroom_id)
        if not room_name:
            raise RuntimeError("Failed to generate room name")

        # Now verify Jitsi server connection
        if not check_jitsi_connection():
            raise RuntimeError("Cannot establish connection with Jitsi server")
            
        # Generate URL and token
        room_url, token = generate_jitsi_url(room_name, current_user.id)
        if not room_url:
            raise RuntimeError("Failed to generate room URL")
        
        # Initialize stream data with validated components
        stream_session = StreamSession(
            room_name=room_name,
            teacher_id=current_user.id,
            url=room_url,
            token=token
        )
        
        # Validate session before storing
        session_dict = stream_session.to_dict()
        if not session_dict.get('room_name'):
            raise RuntimeError("Invalid stream session - missing room name")
            
        # Store the validated session
        active_streams[classroom_id] = stream_session
        
        # Initialize session state
        if classroom_id not in session_states:
            session_states[classroom_id] = {
                'participants': {},
                'is_active': True,
                'connection_issues': []
            }
        
        # Add teacher to participants
        if classroom_id not in room_participants:
            room_participants[classroom_id] = set()
        room_participants[classroom_id].add(current_user.id)
        
        # Update session state
        update_session_state(classroom_id, current_user.id)
        
        return stream_session.__dict__
        
    except Exception as e:
        # Clean up on failure
        if classroom_id in active_streams:
            del active_streams[classroom_id]
        raise RuntimeError(f"Failed to start stream: {str(e)}")

# Handle start stream WebSocket event
@socketio.on('start_stream')
def handle_start_stream(data):
    """Start a new streaming session"""
    if not current_user.is_authenticated or current_user.role != 'teacher':
        emit('stream_error', {'message': 'غير مسموح لك ببدء البث'})
        return
    
    classroom_id = data.get('classroom_id')
    if not classroom_id:
        emit('stream_error', {'message': 'معرف الفصل غير موجود'})
        return
    
    try:
        # Start stream and get session data
        stream_data = start_stream(classroom_id)
        if not stream_data or not isinstance(stream_data, dict):
            raise RuntimeError("Invalid stream data generated")

        # Add classroom tracking information
        app.logger.info(f"Starting stream for classroom {classroom_id}")
        app.logger.debug(f"Stream data: {stream_data}")
        
        # Notify all users in the classroom
        emit('stream_started', {
            'classroom_id': classroom_id,
            'room_name': stream_data.get('room_name'),
            'token': stream_data.get('token'),
            'url': stream_data.get('url'),
            'config': DEFAULT_CONFIG,
            'interface_config': INTERFACE_CONFIG
        }, room=f'classroom_{classroom_id}')
    except Exception as e:
        emit('stream_error', {'message': str(e)})

def end_stream(classroom_id):
    """End a streaming session"""
    if classroom_id not in active_streams:
        return False
        
    try:
        # Remove from active streams
        stream_session = active_streams.pop(classroom_id)
        
        # Clear participants
        if classroom_id in room_participants:
            room_participants[classroom_id].clear()
            del room_participants[classroom_id]
            
        # Update session state
        if classroom_id in session_states:
            session_states[classroom_id]['is_active'] = False
            
        return True
    except Exception as e:
        print(f"Error ending stream: {e}")
        return False

@socketio.on('end_stream')
def handle_end_stream(data):
    """End an active streaming session"""
    if not current_user.is_authenticated or current_user.role != 'teacher':
        emit('stream_error', {'message': 'غير مسموح لك بإنهاء البث'})
        return
    
    classroom_id = data.get('classroom_id')
    if not classroom_id:
        emit('stream_error', {'message': 'معرف الفصل غير موجود'})
        return
    
    if end_stream(classroom_id):
        # Notify all users
        emit('stream_ended', {
            'classroom_id': classroom_id
        }, room=f'classroom_{classroom_id}')

@socketio.on('stream_quality')
def handle_stream_quality(data):
    """Handle stream quality updates"""
    if not current_user.is_authenticated:
        return
        
    classroom_id = session.get('classroom_id')
    if not classroom_id:
        return
        
    quality = data.get('quality', {})
    
    # تحديث جودة البث للفصل
    if classroom_id in session_manager._sessions:
        session_manager._sessions[classroom_id]['stream_quality'].update(quality)
        
    # إخطار المشاركين بتغيير الجودة
    emit('quality_changed', {
        'user_id': current_user.id,
        'quality': quality
    }, room=f'classroom_{classroom_id}')

@socketio.on('connection_lost')
def handle_connection_lost():
    """Handle temporary connection loss"""
    if not current_user.is_authenticated:
        return
        
    classroom_id = session.get('classroom_id')
    if not classroom_id:
        return
        
    # تحديث حالة الاتصال
    session_manager.update_connection_status(
        classroom_id=classroom_id,
        user_id=current_user.id,
        status='reconnecting'
    )
    
    # محاولة إعادة الاتصال
    reconnect_attempts = session_manager._reconnection_attempts.get(classroom_id, {}).get(current_user.id, 0)
    
    if reconnect_attempts < session_manager.MAX_RECONNECT_ATTEMPTS:
        # زيادة عدد محاولات إعادة الاتصال
        session_manager._reconnection_attempts[classroom_id][current_user.id] = reconnect_attempts + 1
        
        # إرسال حالة إعادة الاتصال
        emit('reconnection_status', {
            'attempt': reconnect_attempts + 1,
            'max_attempts': session_manager.MAX_RECONNECT_ATTEMPTS,
            'delay': session_manager.RECONNECT_DELAY
        })
        
        # إخطار المشاركين الآخرين
        emit('user_reconnecting', {
            'user_id': current_user.id,
            'user_name': current_user.name,
            'attempt': reconnect_attempts + 1
        }, room=f'classroom_{classroom_id}')

# Connection monitoring
def monitor_stream_connection(classroom_id):
    """Monitor the connection status of an active stream
    Args:
        classroom_id (int): ID of the classroom to monitor
    Returns:
        dict: Current connection status and metrics
    """
    if classroom_id not in active_streams:
        return {'status': 'inactive'}
        
    stream_data = active_streams[classroom_id]
    current_time = time.time()
    
    # Check connection periodically
    if current_time - stream_data.get('connection_check', 0) > 30:
        try:
            if not check_jitsi_connection():
                stream_data['connection_status'] = 'unstable'
                stream_data['retry_count'] += 1
                
                # Log connection issue
                if classroom_id in session_states:
                    session_states[classroom_id]['connection_issues'].append({
                        'time': current_time,
                        'type': 'connection_lost'
                    })
                
                # If too many retries, end stream
                if stream_data['retry_count'] >= JITSI_RETRY_ATTEMPTS:
                    end_stream(classroom_id)
                    return {'status': 'ended', 'reason': 'connection_failed'}
            else:
                stream_data['connection_status'] = 'connected'
                stream_data['retry_count'] = 0
                
            stream_data['connection_check'] = current_time
            
        except Exception as e:
            stream_data['connection_status'] = 'error'
            stream_data['last_error'] = str(e)
    
    return {
        'status': stream_data['connection_status'],
        'uptime': current_time - stream_data['start_time'],
        'participants': len(room_participants.get(classroom_id, set())),
        'retry_count': stream_data['retry_count']
    }

@socketio.on('check_stream_status')
def handle_stream_status_check(data):
    """Socket.IO handler for stream status checks"""
    classroom_id = data.get('classroom_id')
    if classroom_id:
        status = monitor_stream_connection(classroom_id)
        emit('stream_status_update', {
            'classroom_id': classroom_id,
            'status': status
        })
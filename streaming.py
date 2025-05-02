import logging
from flask import request, session
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
from app import socketio, db
from models import User, Classroom

# Dictionary to track active streams by classroom
active_streams = {}
# Dictionary to track users in rooms
room_participants = {}

@socketio.on('connect')
def handle_connect():
    """
    Handle client connection
    """
    if current_user.is_authenticated:
        logging.info(f"User {current_user.id} connected")
        emit('connection_response', {'status': 'success', 'message': f'مرحبًا {current_user.name}'})
    else:
        logging.info("Unauthenticated user connected")
        emit('connection_response', {'status': 'error', 'message': 'يجب تسجيل الدخول أولاً'})

@socketio.on('disconnect')
def handle_disconnect():
    """
    Handle client disconnection
    """
    if current_user.is_authenticated:
        logging.info(f"User {current_user.id} disconnected")
        # Check if user was in any classroom rooms and leave
        for room_id in list(room_participants.keys()):
            if current_user.id in room_participants[room_id]:
                leave_classroom_room(room_id)

@socketio.on('join_classroom')
def handle_join_classroom(data):
    """
    Handle a user joining a classroom
    """
    if not current_user.is_authenticated:
        emit('join_response', {'status': 'error', 'message': 'يجب تسجيل الدخول أولاً'})
        return
    
    classroom_id = data.get('classroom_id')
    if not classroom_id:
        emit('join_response', {'status': 'error', 'message': 'معرف الفصل غير صالح'})
        return
    
    # Convert to string for room name
    room = f"classroom_{classroom_id}"
    
    # Join the room
    join_room(room)
    
    # Add user to room participants
    if room not in room_participants:
        room_participants[room] = []
    
    if current_user.id not in room_participants[room]:
        room_participants[room].append(current_user.id)
    
    # Get classroom info
    classroom = Classroom.query.get(classroom_id)
    if not classroom:
        emit('join_response', {'status': 'error', 'message': 'الفصل غير موجود'})
        leave_room(room)
        return
    
    # Notify other users in the room
    emit('user_joined', {
        'user_id': current_user.id,
        'user_name': current_user.name,
        'user_role': current_user.role
    }, room=room, include_self=False)
    
    # Get current participants
    participants = []
    for user_id in room_participants[room]:
        user = User.query.get(user_id)
        if user:
            participants.append({
                'id': user.id,
                'name': user.name,
                'role': user.role
            })
    
    # Respond to the client
    emit('join_response', {
        'status': 'success',
        'message': f'تم الانضمام إلى فصل {classroom.name}',
        'classroom': {
            'id': classroom.id,
            'name': classroom.name,
            'subject': classroom.subject,
            'teacher': classroom.teacher.name,
            'is_streaming': room in active_streams
        },
        'participants': participants
    })

@socketio.on('leave_classroom')
def handle_leave_classroom(data):
    """
    Handle a user leaving a classroom
    """
    classroom_id = data.get('classroom_id')
    if not classroom_id:
        emit('leave_response', {'status': 'error', 'message': 'معرف الفصل غير صالح'})
        return
    
    room = f"classroom_{classroom_id}"
    leave_classroom_room(room)
    
    emit('leave_response', {'status': 'success', 'message': 'تم الخروج من الفصل'})

def leave_classroom_room(room):
    """
    Helper function to handle a user leaving a classroom room
    """
    if room in room_participants and current_user.id in room_participants[room]:
        room_participants[room].remove(current_user.id)
        
        # If room is empty, remove it
        if len(room_participants[room]) == 0:
            del room_participants[room]
            # If there was an active stream, end it
            if room in active_streams:
                del active_streams[room]
        
        # Notify other users in the room
        emit('user_left', {
            'user_id': current_user.id,
            'user_name': current_user.name
        }, room=room)
        
        # Leave the socket.io room
        leave_room(room)

@socketio.on('start_stream')
def handle_start_stream(data):
    """
    Handle starting a classroom stream (teacher only)
    """
    if not current_user.is_authenticated:
        emit('stream_response', {'status': 'error', 'message': 'يجب تسجيل الدخول أولاً'})
        return
    
    classroom_id = data.get('classroom_id')
    if not classroom_id:
        emit('stream_response', {'status': 'error', 'message': 'معرف الفصل غير صالح'})
        return
    
    # Check if user is the teacher of this classroom
    classroom = Classroom.query.get(classroom_id)
    if not classroom:
        emit('stream_response', {'status': 'error', 'message': 'الفصل غير موجود'})
        return
    
    if classroom.teacher_id != current_user.id and current_user.role != 'admin':
        emit('stream_response', {'status': 'error', 'message': 'يجب أن تكون معلم هذا الفصل لبدء البث'})
        return
    
    room = f"classroom_{classroom_id}"
    
    # Add to active streams
    active_streams[room] = {
        'teacher_id': current_user.id,
        'start_time': db.func.now()
    }
    
    # Notify everyone in the room
    emit('stream_started', {
        'classroom_id': classroom_id,
        'teacher_id': current_user.id,
        'teacher_name': current_user.name
    }, room=room)
    
    emit('stream_response', {'status': 'success', 'message': 'تم بدء البث المباشر'})

@socketio.on('end_stream')
def handle_end_stream(data):
    """
    Handle ending a classroom stream (teacher only)
    """
    if not current_user.is_authenticated:
        emit('stream_response', {'status': 'error', 'message': 'يجب تسجيل الدخول أولاً'})
        return
    
    classroom_id = data.get('classroom_id')
    if not classroom_id:
        emit('stream_response', {'status': 'error', 'message': 'معرف الفصل غير صالح'})
        return
    
    # Check if user is the teacher of this classroom
    classroom = Classroom.query.get(classroom_id)
    if not classroom:
        emit('stream_response', {'status': 'error', 'message': 'الفصل غير موجود'})
        return
    
    if classroom.teacher_id != current_user.id and current_user.role != 'admin':
        emit('stream_response', {'status': 'error', 'message': 'يجب أن تكون معلم هذا الفصل لإنهاء البث'})
        return
    
    room = f"classroom_{classroom_id}"
    
    # Remove from active streams
    if room in active_streams:
        del active_streams[room]
    
    # Notify everyone in the room
    emit('stream_ended', {
        'classroom_id': classroom_id,
        'teacher_id': current_user.id,
        'teacher_name': current_user.name
    }, room=room)
    
    emit('stream_response', {'status': 'success', 'message': 'تم إنهاء البث المباشر'})

@socketio.on('stream_signal')
def handle_stream_signal(data):
    """
    Handle WebRTC signaling between participants
    """
    if not current_user.is_authenticated:
        return
    
    classroom_id = data.get('classroom_id')
    to_user_id = data.get('to_user_id')
    signal_data = data.get('signal')
    
    if not classroom_id or not to_user_id or not signal_data:
        return
    
    room = f"classroom_{classroom_id}"
    
    # Make sure user is in the room
    if room not in room_participants or current_user.id not in room_participants[room]:
        return
    
    # Forward the signal to the specific user
    emit('stream_signal', {
        'from_user_id': current_user.id,
        'signal': signal_data
    }, room=request.sid)

@socketio.on('chat_message')
def handle_chat_message(data):
    """
    Handle classroom chat messages
    """
    if not current_user.is_authenticated:
        emit('chat_response', {'status': 'error', 'message': 'يجب تسجيل الدخول أولاً'})
        return
    
    classroom_id = data.get('classroom_id')
    message = data.get('message')
    
    if not classroom_id or not message:
        emit('chat_response', {'status': 'error', 'message': 'بيانات غير كاملة'})
        return
    
    room = f"classroom_{classroom_id}"
    
    # Make sure user is in the room
    if room not in room_participants or current_user.id not in room_participants[room]:
        emit('chat_response', {'status': 'error', 'message': 'يجب الانضمام إلى الفصل أولاً'})
        return
    
    # Create message data
    message_data = {
        'user_id': current_user.id,
        'user_name': current_user.name,
        'user_role': current_user.role,
        'message': message,
        'timestamp': db.func.now()
    }
    
    # Broadcast to everyone in the room
    emit('new_chat_message', message_data, room=room)
    emit('chat_response', {'status': 'success'})

@socketio.on('raise_hand')
def handle_raise_hand(data):
    """
    Handle a student raising their hand
    """
    if not current_user.is_authenticated:
        return
    
    classroom_id = data.get('classroom_id')
    if not classroom_id:
        return
    
    room = f"classroom_{classroom_id}"
    
    # Make sure user is in the room
    if room not in room_participants or current_user.id not in room_participants[room]:
        return
    
    # Broadcast to everyone in the room
    emit('hand_raised', {
        'user_id': current_user.id,
        'user_name': current_user.name
    }, room=room)

@socketio.on('lower_hand')
def handle_lower_hand(data):
    """
    Handle a student lowering their hand
    """
    if not current_user.is_authenticated:
        return
    
    classroom_id = data.get('classroom_id')
    if not classroom_id:
        return
    
    room = f"classroom_{classroom_id}"
    
    # Make sure user is in the room
    if room not in room_participants or current_user.id not in room_participants[room]:
        return
    
    # Broadcast to everyone in the room
    emit('hand_lowered', {
        'user_id': current_user.id,
        'user_name': current_user.name
    }, room=room)
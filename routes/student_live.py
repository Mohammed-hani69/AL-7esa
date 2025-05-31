from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from models import User, Role, Classroom, ClassroomEnrollment
from app import db

def is_mobile():
    """Check if current request is from a mobile device"""
    user_agent = request.headers.get('User-Agent', '').lower()
    return any(device in user_agent for device in ['android', 'iphone', 'ipad', 'mobile'])

# Append to the student_bp from the original student.py
from routes.student import student_bp, student_required

@student_bp.route('/classroom/<int:classroom_id>/live')
@login_required
@student_required
def live_classroom(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # Check if student is enrolled
    enrollment = ClassroomEnrollment.query.filter_by(
        user_id=current_user.id,
        classroom_id=classroom.id,
        is_active=True
    ).first()
    
    if not enrollment:
        flash('يجب أن تكون مسجلاً في الفصل للوصول إليه', 'danger')
        return redirect(url_for('student.dashboard'))
    
    template = 'student/mobile-theme/live_class.html' if is_mobile() else 'student/live_class.html'
    return render_template(template, classroom=classroom, enrollment=enrollment)
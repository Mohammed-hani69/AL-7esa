
"""
المسارات الرئيسية للتطبيق
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import current_user, login_required
from models import Role, User, ClassroomEnrollment, Classroom, SubscriptionPlan
from app import db

# تعريف المسارات الأساسية
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """الصفحة الرئيسية"""
    try:
        # عرض الصفحة الرئيسية للزائر
        if not current_user.is_authenticated:
            featured_classrooms = Classroom.query.filter_by(is_free=True).limit(3).all()
            plans = SubscriptionPlan.query.all()
            return render_template('index.html', featured_classrooms=featured_classrooms, plans=plans)
        
        # توجيه المستخدم بناءً على دوره
        if current_user.role == Role.ADMIN:
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == Role.TEACHER:
            return redirect(url_for('teacher.dashboard'))
        elif current_user.role == Role.STUDENT:
            return redirect(url_for('student.dashboard'))
        elif current_user.role == Role.ASSISTANT:
            return redirect(url_for('assistant.dashboard'))
        
        # في حالة وجود خطأ في الدور
        return render_template('index.html')
    except Exception as e:
        current_app.logger.error(f"خطأ في الصفحة الرئيسية: {str(e)}")
        return render_template('index.html')

@main_bp.route('/about')
def about():
    """صفحة من نحن"""
    return render_template('about.html')

@main_bp.route('/contact')
def contact():
    """صفحة اتصل بنا"""
    return render_template('contact.html')

@main_bp.route('/terms')
def terms():
    """صفحة الشروط والأحكام"""
    return render_template('terms.html')

@main_bp.route('/privacy')
def privacy():
    """صفحة سياسة الخصوصية"""
    return render_template('privacy.html')

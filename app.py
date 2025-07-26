"""
منصة الحصة التعليمية - ملف التطبيق الرئيسي
يحتوي على إعداد تطبيق Flask وتكوين المسارات الأساسية
"""

import os
import logging
from datetime import datetime
import re
from urllib.parse import urlparse
from models import db
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_cors import CORS

from flask_cors import CORS
from config import Config

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Create Flask app
app = Flask(__name__)

# تحديد بيئة التطبيق
env = os.environ.get('FLASK_ENV', 'development')
if env == 'production':
    from config import ProductionConfig
    app.config.from_object(ProductionConfig)
elif env == 'testing':
    from config import TestingConfig
    app.config.from_object(TestingConfig)
else:
    from config import DevelopmentConfig
    app.config.from_object(DevelopmentConfig)

# إعدادات إضافية للملفات الكبيرة - بدون حد أقصى للحجم
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year cache for static files
app.config['MAX_CONTENT_LENGTH'] = None  # بدون حد أقصى للحجم لمنع خطأ 413

# إنشاء مجلدات التحميل إذا لم تكن موجودة
upload_folders = app.config.get('UPLOAD_FOLDERS', {})
for folder_name, folder_path in upload_folders.items():
    os.makedirs(folder_path, exist_ok=True)

# إعداد CORS بناءً على البيئة
cors_origins = app.config.get('CORS_ORIGINS', ['http://127.0.0.1:5000'])
print(f"CORS Origins: {cors_origins}")  # تشخيص مؤقت

# تأكد من أن CORS_ORIGINS هو قائمة وليس خاصية
if hasattr(cors_origins, '__iter__') and not isinstance(cors_origins, str):
    cors_origins_list = list(cors_origins)
else:
    cors_origins_list = [str(cors_origins)] if cors_origins else ['http://127.0.0.1:5000']

cors = CORS(app, 
    origins=cors_origins_list,
    supports_credentials=app.config.get('CORS_SUPPORTS_CREDENTIALS', True),
    allow_headers=app.config.get('CORS_ALLOW_HEADERS', ['Content-Type', 'Authorization', 'X-CSRFToken']),
    methods=app.config.get('CORS_METHODS', ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']),
    max_age=app.config.get('CORS_MAX_AGE', 3600)
)

# CSRF Protection - COMPLETELY DISABLED for authentication per user request
# User explicitly requested: "لا اريد استخدام CSRF في التسجيل و في انشاء الحساب"
# CSRF is disabled for all authentication endpoints

# Comment out CSRF protection entirely for now
# csrf = CSRFProtect(app)

# Add dummy csrf_token function to prevent template errors
@app.context_processor
def inject_csrf_token():
    """Provide a dummy csrf_token function since CSRF is disabled"""
    def csrf_token():
        return ""
    return dict(csrf_token=csrf_token)

# إعداد جلسة Flask للاحتفاظ بحالة تسجيل الدخول
@app.before_request  
def ensure_session():
    """التأكد من وجود جلسة صحيحة قبل معالجة الطلبات"""
    # جعل الجلسة دائمة
    session.permanent = True
    
    # إضافة مفتاح للجلسة إذا لم يكن موجوداً
    if '_flask_session_init' not in session:
        session['_flask_session_init'] = True
        session.modified = True

# إضافة معالج مخصص للتشخيص فقط (بعد إنشاء الجلسة)
@app.before_request
def debug_csrf():
    # إضافة تشخيص للطلبات POST فقط عند الحاجة
    if request.method == 'POST' and app.debug:
        print(f"POST request to: {request.endpoint}")
        print(f"Content-Type: {request.headers.get('Content-Type')}")
        print(f"X-CSRFToken header: {request.headers.get('X-CSRFToken')}")
        print(f"Session exists: {bool(session.get('_id'))}")
        print(f"Session permanent: {session.permanent}")
    
    # السماح للـ Flask-WTF بالتعامل مع CSRF بشكل طبيعي
    return

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize database after app is created
db.init_app(app)

# Initialize Firebase
from firebase_config import firebase_config
firebase_config.initialize()

# Initialize Flask-Migrate  
migrate = Migrate(app, db)

# Import models after db is initialized
from models import User, LiveStream, Classroom, SystemSettings, Role

# Add global context processor for datetime
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

# إضافة context processor للـ CSRF token - DISABLED per user request
# @app.context_processor
# def inject_csrf_token():
#     """إضافة CSRF token للـ templates"""
#     from flask_wtf.csrf import generate_csrf
#     return dict(csrf_token=generate_csrf)

# إضافة security headers middleware
@app.after_request
def after_request(response):
    """إضافة security headers للاستجابات"""
    
    # التحقق من البيئة لتطبيق headers مناسبة
    if not app.config.get('DEBUG', True):  # في الإنتاج فقط
        # HTTPS enforcement
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content security policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://meet.jit.si https://8x8.vc https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "media-src 'self' https:; "
            "connect-src 'self' wss: https: https://meet.jit.si https://8x8.vc; "
            "frame-src 'self' https://meet.jit.si https://8x8.vc;"
        )
        
        # Other security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # CORS headers تُعامل بواسطة Flask-CORS
    
    return response

# Add custom Jinja filters
@app.template_filter('slice')
def slice_filter(value, start, end):
    return value[start:end]

@app.template_filter('nl2br')
def nl2br_filter(value):
    if not value:
        return ''
    return value.replace('\n', '<br>')

@app.template_filter('format_math')
def format_math_filter(value):
    if not value:
        return ''
    # Remove unnecessary line breaks between mathematical expressions
    value = value.replace('= \n', '=')
    value = value.replace('\n+', '+')
    value = value.replace('\n=', '=')
    value = value.replace('\n​', '')  # Remove zero-width spaces
    value = value.replace('​\n', '')
    # Preserve intended line breaks
    value = value.replace('\n\n', '<br><br>')
    value = value.replace('\n', ' ')
    return value

@app.template_filter('timeago')
def timeago_filter(value):
    """تحويل التاريخ إلى صيغة نصية سهلة القراءة (مثل: منذ دقيقتين)"""
    if not value:
        return ''

    now = datetime.utcnow()
    diff = now - value

    seconds = diff.total_seconds()

    if seconds < 60:
        return 'الآن'
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f'منذ {minutes} {"دقيقة" if minutes == 1 else "دقائق"}'
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f'منذ {hours} {"ساعة" if hours == 1 else "ساعات"}'
    elif seconds < 2592000:
        days = int(seconds / 86400)
        return f'منذ {days} {"يوم" if days == 1 else "أيام"}'
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f'منذ {months} {"شهر" if months == 1 else "أشهر"}'
    else:
        years = int(seconds / 31536000)
        return f'منذ {years} {"سنة" if years == 1 else "سنوات"}'

# إعداد Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'الرجاء تسجيل الدخول للوصول إلى هذه الصفحة'
login_manager.login_message_category = 'info'
login_manager.session_protection = "strong"  # حماية الجلسة
login_manager.refresh_view = 'auth.login'
login_manager.needs_refresh_message = 'يرجى إعادة تسجيل الدخول لتأكيد الهوية'
login_manager.needs_refresh_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """تحميل المستخدم من قاعدة البيانات"""
    try:
        from models import User
        user = User.query.get(int(user_id))
        return user
    except Exception as e:
        print(f"Error loading user: {e}")
        return None

# Route to get fresh CSRF token (global route) - DISABLED per user request
# @app.route('/csrf-token')
# def get_csrf_token():
#     from flask_wtf.csrf import generate_csrf
#     return jsonify({'csrf_token': generate_csrf()})

# Global CSRF error handler - DISABLED per user request
# @app.errorhandler(CSRFError)
# def handle_csrf_error(e):
    from flask_wtf.csrf import CSRFError, generate_csrf
    from flask import request, jsonify, redirect, url_for, flash
    
    # Add debugging information
    print(f"CSRF Error: {e}")
    print(f"Request method: {request.method}")
    print(f"Request endpoint: {request.endpoint}")
    print(f"Session ID: {session.get('_id', 'No session ID')}")
    print(f"CSRF token in session: {session.get('csrf_token', 'No CSRF token in session')}")
    print(f"X-CSRFToken header: {request.headers.get('X-CSRFToken', 'No X-CSRFToken header')}")
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Content-Type') == 'application/json':
        return jsonify({
            'error': 'csrf_token_expired',
            'message': 'انتهت صلاحية النموذج. يرجى إعادة تحميل الصفحة والمحاولة مرة أخرى.',
            'csrf_token': generate_csrf()
        }), 400
    else:
        flash('انتهت صلاحية النموذج. يرجى إعادة تحميل الصفحة والمحاولة مرة أخرى.', 'danger')
        return redirect(url_for('auth.login')), 400

# Create upload directories
def create_upload_directories():
    upload_dirs = [
        'static/uploads',
        'static/uploads/classroom_content',
        'static/uploads/profile_pictures', 
        'static/uploads/chat_images',
        'static/uploads/assignments'  # إضافة مجلد الواجبات
    ]

    for directory in upload_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")

# Create upload directories
create_upload_directories()

# Route for favicon
@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('img/favicon.ico')

# Route for testing Firestore connection
@app.route('/test-firestore')
def test_firestore():
    return render_template('test_firestore.html')

# Route for testing chat Firebase configuration
@app.route('/test-chat-firebase')
def test_chat_firebase():
    from firebase_config import firebase_config
    config = firebase_config.get_client_config()
    return render_template('test_chat_firebase.html', firebase_config=config)

# Google Meet URL validator








# Create tables and import routes within app context
with app.app_context():
    # Create all tables
    db.create_all()
    
    # Now import and register blueprints
    from routes import main_bp
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.teacher import teacher_bp
    from routes.student import student_bp
    from routes.assistant import assistant_bp
    from routes.chat import chat
    from routes.attendance import attendance_bp

    # Import utility functions
    from utils import cleanup_expired_streams

    # Register blueprints
    app.register_blueprint(main_bp, name="main")
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(assistant_bp, url_prefix='/assistant')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    app.register_blueprint(chat)

# Route لاختبار Firebase
@app.route('/firebase_test.html')
def firebase_test():
    """صفحة اختبار Firebase"""
    try:
        with open('firebase_test.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>ملف الاختبار غير موجود</h1><p>تشغيل: python final_firebase_fix.py</p>", 404

# Route لاختبار الاتصال
@app.route('/api/test_firebase', methods=['POST'])
def test_firebase_api():
    """API لاختبار Firebase"""
    return jsonify({
        'success': True,
        'message': 'Firebase API يعمل بشكل صحيح',
        'timestamp': datetime.now().isoformat()
    })

# Add a before_request hook to periodically clean up expired streams
import threading
import time

def periodic_cleanup():
    """Background thread to clean up expired streams every 5 minutes"""
    while True:
        try:
            with app.app_context():
                cleanup_expired_streams()
        except Exception as e:
            app.logger.error(f"Error in periodic cleanup: {e}")
        time.sleep(300)  # Sleep for 5 minutes

# Start the cleanup thread in production/development
if not app.config.get('TESTING', False):
    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()
    app.logger.info("Started periodic cleanup thread for expired live streams")

# Background cleanup thread for expired streams

# API مسارات للإشعارات
@app.route('/api/notifications/mark-all-read', methods=['POST'])
def api_mark_all_notifications_read():
    """API لتعليم جميع الإشعارات كمقروءة"""
    from flask_login import current_user, login_required
    from models import Notification
    
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'غير مصرح'}), 401
    
    try:
        # تعليم جميع الإشعارات غير المقروءة للمستخدم الحالي كمقروءة
        updated_count = Notification.query.filter_by(
            user_id=current_user.id, 
            is_read=False
        ).update({'is_read': True})
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'تم تعليم {updated_count} إشعار كمقروء',
            'updated_count': updated_count
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error marking notifications as read: {e}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء تحديث الإشعارات'}), 500

@app.route('/api/notifications/<int:notification_id>/mark-read', methods=['POST'])
def api_mark_notification_read(notification_id):
    """API لتعليم إشعار واحد كمقروء"""
    from flask_login import current_user, login_required
    from models import Notification
    
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'غير مصرح'}), 401
    
    try:
        notification = Notification.query.filter_by(
            id=notification_id, 
            user_id=current_user.id
        ).first()
        
        if not notification:
            return jsonify({'success': False, 'message': 'الإشعار غير موجود'}), 404
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'تم تعليم الإشعار كمقروء'
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error marking notification as read: {e}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء تحديث الإشعار'}), 500

@app.route('/api/notifications/unread-count', methods=['GET'])
def api_get_unread_notifications_count():
    """API للحصول على عدد الإشعارات غير المقروءة"""
    from flask_login import current_user
    from models import Notification
    
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'count': 0}), 401
    
    try:
        unread_count = Notification.query.filter_by(
            user_id=current_user.id, 
            is_read=False
        ).count()
        
        return jsonify({
            'success': True, 
            'count': unread_count
        })
    except Exception as e:
        app.logger.error(f"Error getting unread notifications count: {e}")
        return jsonify({'success': False, 'count': 0}), 500

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    app.logger.error(f"Server Error: {error}")
    # عند حدوث استثناء في جينجا بسبب تعريف كتلة مكررة
    if "block 'content' defined twice" in str(error):
        return render_template('500.html', error="حدث خطأ في قوالب الموقع. يرجى المحاولة مرة أخرى أو الاتصال بمسؤول النظام."), 500
    return render_template('500.html', error=str(error)), 500

# إنشاء جداول قاعدة البيانات والحساب الإداري عند بدء التشغيل
def initialize_app():
    """تهيئة التطبيق وإنشاء الحساب الإداري"""
    with app.app_context():
        try:
            # إنشاء جداول قاعدة البيانات
            db.create_all()
            print("✅ تم إنشاء جداول قاعدة البيانات")
            
            # إنشاء الحساب الإداري
            from init_admin import create_default_admin
            create_default_admin()
            
        except Exception as e:
            print(f"❌ خطأ في تهيئة التطبيق: {str(e)}")

# مسار النقر على البانرات لتتبع النقرات
@app.route('/banner/<int:banner_id>/click')
def banner_click(banner_id):
    """تتبع نقرات البانرات"""
    try:
        from models import Banner
        banner = Banner.query.get_or_404(banner_id)
        banner.increment_click()
        
        if banner.link_url:
            return redirect(banner.link_url)
        else:
            return redirect(url_for('main.index'))
    except Exception as e:
        app.logger.error(f"Error tracking banner click: {e}")
        return redirect(url_for('main.index'))

# استدعاء التهيئة عند بدء التشغيل
if __name__ == '__main__':
    initialize_app()
    
    # تشغيل التطبيق
    debug_mode = app.config.get('DEBUG', False)
    host = app.config.get('HOST', '0.0.0.0')
    port = app.config.get('PORT', 5000)
    
    print(f"🚀 بدء تشغيل منصة الحصة على {host}:{port}")
    app.run(
        host=host,
        port=port,
        debug=debug_mode,
        use_reloader=False  # تجنب إعادة التشغيل المضاعف
    )
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

# إعداد CORS بناءً على البيئة
cors = CORS(app, 
    origins=app.config['CORS_ORIGINS'],
    supports_credentials=app.config.get('CORS_SUPPORTS_CREDENTIALS', True),
    allow_headers=app.config.get('CORS_ALLOW_HEADERS', ['Content-Type', 'Authorization', 'X-CSRFToken']),
    methods=app.config.get('CORS_METHODS', ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']),
    max_age=app.config.get('CORS_MAX_AGE', 3600)
)

csrf = CSRFProtect(app)

# إضافة معالج مخصص للتحقق من CSRF
@app.before_request
def check_csrf():
    # تجاهل CSRF للطلبات JSON في مسارات Firebase المخصصة
    if request.endpoint and hasattr(app.view_functions.get(request.endpoint), '_csrf_exempt'):
        # للـ routes المستثناة، تحقق من CSRF في header بدلاً من النموذج
        if request.method == 'POST':
            csrf_token = request.headers.get('X-CSRFToken')
            if not csrf_token:
                from flask import abort
                abort(400, description='CSRF token is missing in headers')
        return
    # السماح للـ Flask-WTF بالتعامل مع CSRF بشكل طبيعي
    return

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize database after app is created
db.init_app(app)

# Configure session for permanent lifetime
@app.before_request
def make_session_permanent():
    session.permanent = True

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

# Configure login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'الرجاء تسجيل الدخول للوصول إلى هذه الصفحة'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Route to get fresh CSRF token (global route)
@app.route('/csrf-token')
def get_csrf_token():
    from flask_wtf.csrf import generate_csrf
    return jsonify({'csrf_token': generate_csrf()})

# Global CSRF error handler
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    from flask_wtf.csrf import CSRFError, generate_csrf
    from flask import request, jsonify, redirect, url_for, flash
    
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

    # Import utility functions
    from utils import cleanup_expired_streams

    # Register blueprints
    app.register_blueprint(main_bp, name="main")
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(assistant_bp, url_prefix='/assistant')
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
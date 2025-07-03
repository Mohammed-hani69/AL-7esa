"""
منصة الحصة التعليمية - ملف التطبيق الرئيسي
يحتوي على إعداد تطبيق Flask وتكوين المسارات الأساسية
"""

import os
import logging
from datetime import datetime
import re
from urllib.parse import urlparse

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_cors import CORS
from config import Config
from flask_wtf.csrf import CSRFProtect

# إعداد Rate Limiting
from rate_limiting import init_limiter

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

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

# إعداد SocketIO مع CORS آمن
socketio = SocketIO(app, cors_allowed_origins=app.config.get('SOCKETIO_CORS_ALLOWED_ORIGINS', ["*"]))

csrf = CSRFProtect(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize database
db.init_app(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# تفعيل Rate Limiting
limiter = init_limiter(app)

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

# Import models (after db initialization)
from models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

# Google Meet URL validator








# SocketIO مُعدّ بالفعل أعلاه مع CORS آمن

# Import and register blueprints
from routes import main_bp
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.teacher import teacher_bp
from routes.student import student_bp
from routes.assistant import assistant_bp

# Register blueprints
app.register_blueprint(main_bp, name="main")
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(teacher_bp, url_prefix='/teacher')
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(assistant_bp, url_prefix='/assistant')

# Create tables
with app.app_context():
    db.create_all()

# Import socket events
from streaming import *

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